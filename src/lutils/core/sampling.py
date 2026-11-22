"""Interpolation of cell-centered values at arbitrary points.

`Sampler` builds a search structure over the cell centres once and then
evaluates the cell values at any number of points. Three methods are
available:

* ``"linear"``: weighted least-squares fit of a linear function to the nearest
    cell centres. Exact for linearly varying fields and second-order accurate.
* ``"nearest"``: value of the closest cell centre.
* ``"delaunay"``: linear interpolation on a Delaunay triangulation of the cell
    centres. Built and cached on first use.

Axes along which the cell centres do not vary, such as the single cell layer
of a 2D case, are ignored.
"""

from collections.abc import Sequence
import functools
from typing import Literal, Self

import numpy as np
from numpy.typing import ArrayLike
from numpy.typing import NDArray
import polars as pl
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree
from scipy.spatial import Delaunay

from lutils._typing import Point
from lutils.core.data import FieldData

type Method = Literal["linear", "nearest", "delaunay"]
"""Interpolation method accepted by the sampling methods."""

type Points = ArrayLike | pl.DataFrame
"""Sample points: an ``(m, 3)`` array, a single point, or a frame with
``x, y, z`` columns."""

_AXES: tuple[str, str, str] = ("x", "y", "z")
# Axis whose spread is below this fraction of the domain size is flat
_FLAT_TOLERANCE = 1e-6
_WEIGHT_OFFSET = 1e-6
# Query points fitted per batch
_CHUNK = 65536
# A fit with smallest value below this fraction is rank-deficient
_CONDITION_LIMIT = 1e-3
# Ill-conditioned fits are retried with times this neighbours,
# up to the limit
_NEIGHBOUR_GROWTH = 4
_MAX_NEIGHBOURS = 256


class Sampler:
    """Evaluates cell-centered values at arbitrary points.

    Attributes:
        names: Names of the sampled value columns.
        dimensions: Number of axes along which the cell centres vary.
        neighbours: Number of cell centres used by the ``"linear"`` method.
    """

    def __init__(
        self,
        centres: ArrayLike,
        values: ArrayLike,
        *,
        names: Sequence[str] | None = None,
        ids: ArrayLike | None = None,
        neighbours: int = 8,
    ) -> None:
        """Builds the search tree over the cell centres.

        Args:
            centres: Cell centres with shape ``(n, 3)``.
            values: Cell values with shape ``(n,)`` or ``(n, k)`` for ``k``
                fields or components.
            names: Names of the ``k`` value columns in sampled frames. If
                None, ``value`` for a single column, otherwise ``value0``,
                ``value1``, ...
            ids: Cell labels with shape ``(n,)`` returned by `nearest`. If
                None, the row index is used.
            neighbours: Number of nearest cell centres for the ``"linear"``
                method. Must be greater than the number of dimensions.

        Raises:
            ValueError: If the shapes do not match, the names are not unique
                or clash with ``s, x, y, z``, the centres span fewer than two
                dimensions, or there are too few neighbours for a linear fit.
        """
        points = np.asarray(centres, dtype=np.float64)
        data = np.asarray(values, dtype=np.float64)

        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(
                f"centres must have shape (n, 3), got {points.shape}"
            )
        if data.shape[:1] != points.shape[:1] or data.ndim not in (1, 2):
            raise ValueError(
                f"values must have shape ({len(points)},) or "
                f"({len(points)}, k), got {data.shape}"
            )

        self._scalar = data.ndim == 1
        self._values = data.reshape(len(data), -1)
        self.names = _value_names(names, self._values.shape[1])
        self._ids = _cell_ids(ids, len(points))

        self._active = _active_axes(points)
        self.dimensions = int(self._active.sum())
        self.neighbours = min(neighbours, len(points))
        if self.neighbours <= self.dimensions:
            raise ValueError(
                f"linear fit in {self.dimensions}D needs more than "
                f"{self.dimensions} neighbours, got {self.neighbours}"
            )

        self._points = np.ascontiguousarray(points[:, self._active])
        self._tree = cKDTree(self._points)

    @classmethod
    def from_data(
        cls,
        data: FieldData,
        fields: Sequence[str] | None = None,
        *,
        neighbours: int = 8,
    ) -> Self:
        """Builds a sampler over the cells of a `FieldData`.

        Args:
            data: The cells to sample from.
            fields: Field columns to sample. If None, all fields are used.
            neighbours: Number of nearest cell centres for the ``"linear"``
                method.

        Returns:
            A sampler whose value columns are named after the fields and
            whose `nearest` returns ``cellI``.

        Raises:
            TypeError: If ``fields`` is a single string.
            ValueError: If no fields are selected or a field is missing.
        """
        if isinstance(fields, str):
            raise TypeError(
                "fields must be a sequence of names, not a single str"
            )
        names = data.fields if fields is None else list(fields)
        if not names:
            raise ValueError("no fields to sample")

        missing = [name for name in names if name not in data.columns]
        if missing:
            raise ValueError(
                f"missing fields {missing}, available: {data.fields}"
            )

        return cls(
            data.frame.select(_AXES).to_numpy(),
            data.frame.select(names).to_numpy(),
            names=names,
            ids=data.frame.get_column("cellI").to_numpy(),
            neighbours=neighbours,
        )

    def at(
        self,
        points: Points,
        *,
        method: Method = "linear",
        max_distance: float | None = None,
    ) -> pl.DataFrame:
        """Samples the values at the given points.

        Args:
            points: Sample points. If a frame is given, all its columns are
                kept and the sampled values are appended.
            method: Interpolation method, see the module description.
            max_distance: If given, samples whose nearest cell centre is
                farther away are set to NaN. Use to avoid extraplating outside
                the domain or across holes.

        Returns:
            The points (or the input frame) with one column per value.

        Raises:
            ValueError: If the points are malformed, ``method`` is unknown,
                or a value name is already a column of the input frame.
        """
        coordinates = _coordinates(points)
        values = self._sample(coordinates, method, max_distance)
        sampled = pl.DataFrame(dict(zip(self.names, values.T, strict=True)))

        if isinstance(points, pl.DataFrame):
            clashes = [name for name in self.names if name in points.columns]
            if clashes:
                raise ValueError(f"points already have columns {clashes}")
            return points.hstack(sampled)

        axes = pl.DataFrame(dict(zip(_AXES, coordinates.T, strict=True)))
        return axes.hstack(sampled)

    def line(
        self,
        start: Point,
        end: Point,
        count: int = 200,
        *,
        method: Method = "linear",
        max_distance: float | None = None,
    ) -> pl.DataFrame:
        """Samples the values at evenly spaced points along a line segment.

        Args:
            start: First end point ``(x , y, z)``.
            end: Second end point ``(x, y, z)``.
            count: Number of points, including both end points.
            method: Interpolation method, see the module description.
            max_distance: If given, samples whose nearest cell centre is
                farther away are set to NaN.

        Returns:
            A frame with ``s, x, y, z`` and one column per value.

        Raises:
            ValueError: If ``count`` is below 2, ``start`` and ``end``
                coincide, or ``method`` is unknown.
        """
        distance, points = line_points(start, end, count)
        return pl.DataFrame({"s": distance}).hstack(
            self.at(points, method=method, max_distance=max_distance)
        )

    def nearest(self, points: Points) -> NDArray[np.int64]:
        """Finds the nearest cell for each point.

        Args:
            points: Sample points.

        Returns:
            The ids of the nearest cells with shape ``(m,)``: ``cellI`` for a
            sampler built with `from_data`, otherwise the given ``ids`` or
            row indices.

        Raises:
            ValueError: If the points are malformed.
        """
        _, rows = self._tree.query(self._restrict(_coordinates(points)))
        return self._ids[np.asarray(rows, dtype=np.intp)]

    @functools.cached_property
    def _triangulation(self) -> Delaunay:
        """Delaunay triangulation of the cell centres, build on first use."""
        return Delaunay(self._points)

    def _restrict(
        self, coordinates: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Restricts points to the axes along which the centres vary.

        Args:
            coordinates: Points with shape ``(m, 3)``.

        Returns:
            The points with the flat axes removed.
        """
        return coordinates[:, self._active]

    def _sample(
        self,
        coordinates: NDArray[np.float64],
        method: Method,
        max_distance: float | None,
    ) -> NDArray[np.float64]:
        """Samples the values at points given as an ``(m, 3)`` array.

        Args:
            coordinates: Sample points with shape ``(m, 3)``.
            method: Interpolation method.
            max_distance: Distance limit to the nearest cell centre, if any.

        Returns:
            The values with shape ``(m, k)``.

        Raises:
            ValueError: If ``method`` is unknown.
        """
        queries = self._restrict(coordinates)
        distances: NDArray[np.float64] | None

        if method == "linear":
            distances, values = self._linear(queries)
        elif method == "nearest":
            nearest, rows = self._tree.query(queries)
            distances = np.asarray(nearest, dtype=np.float64)
            values = self._values[np.asarray(rows, dtype=np.float64)]
        elif method == "delaunay":
            interpolator = LinearNDInterpolator(
                self._triangulation, self._values
            )
            values = interpolator(queries)
            distances = None
        else:
            raise ValueError(f"unknown method {method!r}")

        if max_distance is not None:
            if distances is None:
                nearest, _ = self._tree.query(queries)
                distances = np.asarray(nearest, dtype=np.float64)
            values[distances > max_distance] = np.nan
        return values

    def _linear(
        self, queries: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Weighted least-squares linear fit over the nearest cell centres.

        For each query point ``q``, fits ``f(p) = a + g * (p - q)`` to the
        nearest cell values with inverse-distance weights. ``a`` is the
        interpolated value. Offsets are scaled by the neighbourhood radius
        to keep the fit well-scaled. Neighbourhoods that do not span all
        directions are refitted with more neighbours (see `_fit`). Queries
        are processed in batches to bound memory use.

        Args:
            queries: Query points restricted to the active axes.

        Returns:
            The distance to the nearest cell centre with shape ``(m,)`` and
            the values with shape ``(m, k)``.
        """
        nearest = np.empty(len(queries))
        values = np.empty((len(queries), self._values.shape[1]))

        for begin in range(0, len(queries), _CHUNK):
            batch = slice(begin, begin + _CHUNK)
            nearest[batch], values[batch] = self._fit(queries[batch])

        return nearest, values

    def _fit(
        self, queries: NDArray[np.float64], neighbours: int | None = None
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Fits one batch of query points, see `_linear`.

        If the neighbours of a point do not span all directions, as happends
        on strongly stretched cells, the point is refitted with more
        neighbours, up to ``_MAX_NEIGHBOURS``. Directions that stay unresolved
        are dropped from the fit by the pseudo-inverse.

        Args:
            queries: Query points restricted to the active axes.
            neighbours: Number of neighbours to fit, defaults to `neighbours`.

        Returns:
            The distance to the nearest cell centre and the values.
        """
        count = self.neighbours if neighbours is None else neighbours
        distances, indices = self._tree.query(queries, k=count)
        radius = distances[:, -1:].copy()

        offsets = self._points[indices] - queries[:, None, :]
        offsets /= radius[..., None]
        weigths = 1.0 / (distances / radius + _WEIGHT_OFFSET)
        design = np.concatenate(
            (np.ones(indices.shape + (1,)), offsets), axis=-1
        )

        # Weighted pseudo-inverse via SVD, first row maps the neighbout
        # values to the fitted value at the query point
        left, singular, right = np.linalg.svd(
            design * weigths[..., None], full_matrices=False
        )
        resolved = singular > _CONDITION_LIMIT * singular[:, :1]
        inverse = np.divide(
            1.0, singular, where=resolved, out=np.zeros_like(singular)
        )
        coefficients = np.einsum("mj,mkj->mk", right[:, :, 0] * inverse, left)
        coefficients *= weigths
        values = np.einsum("mk,mkf->mf", coefficients, self._values[indices])

        retry = ~resolved.all(axis=1)
        larger = min(
            count * _NEIGHBOUR_GROWTH, _MAX_NEIGHBOURS, len(self._points)
        )
        if retry.any() and larger > count:
            _, values[retry] = self._fit(queries[retry], larger)

        return distances[:, 0], values


def line_points(
    start: Point, end: Point, count: int
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Places evenly spaced points on a line segment.

    Args:
        start: First end point ``(x, y, z)``.
        end: Second end point ``(x, y, z)``.
        count: Number of points, including both end points.

    Returns:
        The distance of each point from ``start`` with shape ``(count,)``
        and the points with shape ``(count, 3)``.

    Raises:
        ValueError: If ``count`` is below 2 or ``start`` and ``end``
            coincide.
    """
    if count < 2:
        raise ValueError(f"count must be at least 2, got {count}")
    origin = np.asarray(start, dtype=np.float64)
    direction = np.asarray(end, dtype=np.float64) - origin

    length = float(np.linalg.norm(direction))
    if length == 0:
        raise ValueError("start and end of the line must differ")

    fractions = np.linspace(0.0, 1.0, count)
    return fractions * length, origin + np.outer(fractions, direction)


def _value_names(names: Sequence[str] | None, count: int) -> tuple[str, ...]:
    """Validates or generates the names of the value columns.

    Args:
        names: Names given by the caller, or None.
        count: Number of value columns.

    Returns:
        One unique name per value column.

    Raises:
        ValueError: If the count is wrong, a name repeats, or a name is one
            of ``s, x, y, z``.
    """
    if names is None:
        if count == 1:
            return ("value",)
        return tuple(f"value{index}" for index in range(count))

    result = tuple(names)
    if len(result) != count:
        raise ValueError(f"expected {count} names, got {len(result)}")
    if len(set(result)) != count:
        raise ValueError(f"names must be unique, got {list(result)}")

    reserved = [name for name in result if name in ("s", *_AXES)]
    if reserved:
        raise ValueError(f"names {reserved} are reserved for coordinates")
    return result


def _cell_ids(ids: ArrayLike | None, count: int) -> NDArray[np.int64]:
    """Validates or generates cell ids returned by `Sampler.nearest`.

    Args:
        ids: Ids given by the caller, or None for row indices.
        count: Number of cells.

    Returns:
        The ids with shape ``(count,)``.

    Raises:
        ValueError: If the number of ids does not match the cell count.
    """
    if ids is None:
        return np.arange(count, dtype=np.int64)

    result = np.asarray(ids, dtype=np.int64)
    if result.shape != (count,):
        raise ValueError(f"ids must have shape ({count},), got {result.shape}")
    return result


def _active_axes(centres: NDArray[np.float64]) -> NDArray[np.bool_]:
    """Finds the axes along which the cell centres vary.

    Args:
        centres: Cell centres with shape ``(n, 3)``.

    Returns:
        A boolean mask over the three axes.

    Raises:
        ValueError: If fewer than two axes vary.
    """
    span = np.ptp(centres, axis=0) if len(centres) else np.zeros(3)
    active = span > _FLAT_TOLERANCE * np.linalg.norm(span)
    if active.sum() < 2:
        raise ValueError("cell centres must vary along at least two axes")
    return active


def _coordinates(points: Points) -> NDArray[np.float64]:
    """Converts sample points to an ``(m, 3)`` array.

    Args:
        points: An ``(m, 3)`` array, a single point, or a frame with
            ``x, y, z`` columns.

    Returns:
        The coordinates with shape ``(m, 3)``.

    Raises:
        ValueError: If a frame lacks ``x, y, z`` or an array does not have
            three coordinates per point.
    """
    if isinstance(points, pl.DataFrame):
        missing = [axis for axis in _AXES if axis not in points.columns]
        if missing:
            raise ValueError(f"points frame is missing columns {missing}")
        return np.asarray(points.select(_AXES).to_numpy(), dtype=np.float64)

    coordinates = np.atleast_2d(np.asarray(points, dtype=np.float64))
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError(
            f"points must have shape (m, 3), got {coordinates.shape}"
        )
    return coordinates
