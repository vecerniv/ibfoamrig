"""Containers for post-processed OpenFOAM data.

Each container wraps a polars frame and offers the selections needed for
post-processing. Containers are immutable, selections return new instances.
"""

from collections.abc import Iterable, Mapping, Sequence
import dataclasses
from typing import ClassVar, Self

import numpy as np
from numpy.typing import NDArray
import polars as pl

from lutils._typing import Point
from lutils._typing import StrPath
from lutils.io import foam_file
from lutils.io import tables

_BASE_COLUMNS: tuple[str, ...] = ("cellI", "x", "y", "z")
# Column suffixes per component count
_SUFFIXES: dict[int, tuple[str, ...]] = {
    1: ("",),
    3: ("x", "y", "z"),
    6: ("xx", "xy", "xz", "yy", "yz", "zz"),
    9: ("xx", "xy", "xz", "yx", "yy", "yz", "zx", "zy", "zz"),
}
# Every non-empty component suffix
_COMPONENT_SUFFIXES: frozenset[str] = frozenset(
    suffix for group in _SUFFIXES.values() for suffix in group if suffix
)
_AXES: tuple[str, ...] = ("x", "y", "z")


@dataclasses.dataclass(frozen=True, slots=True)
class _FrameData:
    """Base class for containers wrapping a polars frame with required columns.

    Attributes:
        frame: The wrapped frame.
    """

    _REQUIRED: ClassVar[tuple[str, ...]] = ()
    frame: pl.DataFrame

    def __post_init__(self) -> None:
        """Check that the frame holds the columns the class requires.

        Raises:
            ValueError: If a required columns in missing.
        """
        missing = [c for c in self._REQUIRED if c not in self.frame.columns]
        if missing:
            raise ValueError(
                f"{type(self).__name__} frame is missing columns {missing}"
            )

    @property
    def columns(self) -> list[str]:
        """The contained column names."""
        return self.frame.columns


@dataclasses.dataclass(frozen=True, slots=True)
class _SpatialData(_FrameData):
    """Base for containers with one point ``x, y, z`` per row."""

    _REQUIRED: ClassVar[tuple[str, ...]] = _BASE_COLUMNS

    def box(self, lower: Point, upper: Point) -> Self:
        """Selects cell whose centres lie inside an axis-aligned box.

        Args:
            lower: Lower corner ``(x, y, z)`` of the box.
            upper: Upper corner ``(x, y, z)`` of the box.

        Returns:
            The selected cells (bound included).
        """
        return dataclasses.replace(
            self, frame=self.frame.filter(_in_box(lower, upper))
        )


@dataclasses.dataclass(frozen=True, slots=True)
class FieldData(_SpatialData):
    """Cell values of one or more fields together with the cell centres.

    Attributes:
        frame: One row per cell with columns ``cellI``, ``x``, ``y``, ``z``,
            and one column per field component.
    """

    @classmethod
    def from_file(
        cls, path: StrPath, *, fields: Sequence[str] | None = None
    ) -> Self:
        """Loads a table written by a function object.

        Args:
            path: Path to the table.
            fields: Field columns to keep. The cell index and centres are
                always kept. If None, all columns are loaded.

        Returns:
            The loaded field data.

        Raises:
            TypeError: If ``fields`` is a single string.
            FileNotFoundError: If the file does not exist.
            FoamParseError: If a requested column is missing from the file.
        """
        if isinstance(fields, str):
            raise TypeError(
                "fields must be a sequence of names, not a single str"
            )
        columns = None if fields is None else [*_BASE_COLUMNS, *fields]

        return cls(frame=tables.read_table(path, columns=columns))

    @classmethod
    def from_fields(
        cls,
        centres: foam_file.FoamField,
        fields: Iterable[foam_file.FoamField],
        volumes: foam_file.FoamField | None = None,
    ) -> Self:
        """Builds field data from OpenFOAM field files.

        Vector and tensor fields are split into one column per component,
        e.g. ``U`` into ``Ux, Uy, Uz``. Uniform fields are expanded to all
        cells.

        Args:
            centres: Cell centres, written by
                ``postProcess -func writeCellCentres``.
            fields: The fields to include.
            volumes: Cell volumes, written by
                ``postProcess -func writeCellVolumes``. Optional.

        Returns:
            The field data, with cells in mesh order.

        Raises:
            ValueError: If ``centres`` is not a nonuniform vector field, a
                field does not match the number of cells, or two columns get
                the same name.
        """
        if centres.is_uniform or centres.components != 3:
            raise ValueError(
                f"centres must a a nonuniform vector field, "
                f"got {centres.name!r} with {centres.components} components"
            )
        size = centres.length

        columns: dict[str, NDArray[np.generic]] = {
            "cellI": np.arange(size, dtype=np.int64)
        }
        _add_columns(columns, centres, size, names=_AXES)

        if volumes is not None:
            _add_columns(columns, volumes, size, names=("V",))

        for field in fields:
            _add_columns(columns, field, size)

        return cls(frame=pl.DataFrame(columns))

    def line(
        self,
        axis: str,
        at: float,
        *,
        tol: float = 1e-6,
        sort_by: str | None = None,
    ) -> Self:
        raise NotImplementedError

    def column(self, name: str) -> pl.Series:
        """Returns the values of one column.

        Args:
            name: Name of the column.

        Returns:
            The column as a polars Series.

        Raises:
            KeyError: If the column does not exist.
        """
        if name not in self.frame.columns:
            raise KeyError(
                f"missing column {name}, available: {self.frame.columns}"
            )

        return self.frame.get_column(name)


@dataclasses.dataclass(frozen=True, slots=True)
class InterpolationData(_SpatialData):
    """IBM interpolation info for each boundary cell.

    Built from ``interpolationInfo_boundary.dat`` and joined with the cell
    centres, so ``x, y, z`` hold the centre of the boundary cell.
    """

    _REQUIRED: ClassVar[tuple[str, ...]] = (
        *_BASE_COLUMNS,
        *(f"surfNorm_{a}" for a in _AXES),
        "intPoint0_x",
    )

    @classmethod
    def from_file(cls, path: StrPath, cells: FieldData) -> Self:
        """Loads interpolation info and joins the boundary cell centres.

        Args:
            path: Path to the file.
            cells: Field data of the same case and time, providing the cell
                centres. Must contain every boundary cell.

        Returns:
            The interpolation data, one row per boundary cell.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If a boundary cell is missing from ``cells``, or the
                file lacks required columns.
        """
        info = tables.read_table(path).drop(_AXES, strict=False)
        centres = cells.frame.select(_BASE_COLUMNS)
        frame = info.join(centres, on="cellI", how="left", validate="m:1")

        unmatched = frame.filter(pl.col("x").is_null()).height
        if unmatched:
            raise ValueError(
                f"{unmatched} boundary cells are missing from cellls"
            )

        # Reorder so _BASE_COLUMNS are first
        rest = [c for c in frame.columns if c not in _BASE_COLUMNS]
        return cls(frame=frame.select(*_BASE_COLUMNS, *rest))

    @property
    def point_count(self) -> int:
        """Number of interpolation points per boundary cell."""
        count = 0
        while f"intPoint{count}_x" in self.frame.columns:
            count += 1

        return count

    def points(self, index: int) -> pl.DataFrame:
        """Returns one interpolation point of every boundary cell.

        Args:
            index: Index of the point, 0 being the point on the surface.

        Returns:
            A frame with ``cellI``, ``x, y, z`` of the point and, if present
            ``intCell``, the cell the solver interpolates from.

        Raises:
            IndexError: If ``index`` is out of range.
        """
        if not 0 <= index < self.point_count:
            raise IndexError(
                f"point index {index} out of range 0..{self.point_count - 1}"
            )
        selection = [
            pl.col("cellI"),
            *(pl.col(f"intPoint{index}_{a}").alias(a) for a in _AXES),
        ]
        if f"intCell{index}" in self.columns:
            selection.append(pl.col(f"intCell{index}").alias("intCell"))

        return self.frame.select(selection)

    def normals(self) -> pl.DataFrame:
        """Returns the surface normal of every boundary cell.

        Returns:
            A frame with ``cellI`` and the normal components ``x, y, z``.
        """
        return self.frame.select(
            "cellI", *(pl.col(f"surfNorm_{a}").alias(a) for a in _AXES)
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ResidualData(_FrameData):
    """Solver residuals over the iterations or time steps of a run."""

    _REQUIRED: ClassVar[tuple[str, ...]] = ("Time",)

    @classmethod
    def from_file(cls, path: StrPath) -> Self:
        """Loads a ``residuals.dat`` file written by OpenFOAM.

        Args:
            path: Path to the file.

        Returns:
            The loaded residuals.

        Raises:
            FileNotFoundError: If the file does not exist.
            FoamParseError: If the file is malformed.
        """
        return cls(frame=tables.read_residuals(path))

    @property
    def fields(self) -> list[str]:
        """Names of the residual columns, without ``Time``."""
        return [c for c in self.columns if c != "Time"]

    def final(self) -> dict[str, float | None]:
        """Returns the residuals of the last iteration.

        Returns:
            A mapping from residuals name to its last value, or None if it
            was not solved in the last iteration.

        Raises:
            ValueError: If the frame has no rows.
        """
        if self.frame.is_empty():
            raise ValueError("no residuals recorded")
        last = self.frame.tail(1).row(0, named=True)

        return {name: last[name] for name in self.fields}

    def is_converged(self, tol: float | Mapping[str, float]) -> bool:
        """Checks whether the last residuals are below a tolerance.

        Args:
            tol: One tolerance for all residuals, or a mapping from name to
                tolerance. Name is either a column or the base name of a
                vector or tensor, which covers all its components. Residuals
                missing from the mapping are not checked.

        Returns:
            True if every checked residual is below its tolerance. A null
            residual counts as not converged.

        Raises:
            KeyError: If a name in ``tol`` matches no residual column.
            ValueError: If the frame has no rows.
        """
        final = self.final()
        if not isinstance(tol, Mapping):
            limits = dict.fromkeys(final, tol)
        else:
            limits = {}
            for name, value in tol.items():
                for column in self._columns_for(name):
                    limits[column] = value

        return all(
            (residual := final[column]) is not None and residual < limit
            for column, limit in limits.items()
        )

    def _columns_for(self, name: str) -> list[str]:
        """Resolves a residual name to its columns.

        Args:
            name: A column name or the base name of a vector or tensor
                field, which covers all of its component columns.

        Returns:
            The matching columns in frame order.

        Raises:
            KeyError: If nothing matches.
        """
        for name in self.fields:
            return [name]
        columns = [
            column
            for column in self.fields
            if column.startswith(name)
            and column[len(name) :] in _COMPONENT_SUFFIXES
        ]
        if not columns:
            raise KeyError(
                f"no residual matches {name!r}, available: {self.fields}"
            )

        return columns


def _add_columns(
    columns: dict[str, NDArray[np.generic]],
    field: foam_file.FoamField,
    size: int,
    names: Sequence[str] | None = None,
) -> None:
    """Adds one columns per component of a field.

    Args:
        columns: Columns collected so far, updated in place.
        field: The field to add.
        size: Number of cells, uniform fields are expanded to it.
        names: Column names to use. If None, they are built from the field
            name and components suffixes.

    Raises:
        ValueError: If the field has th wrong length or component count, ot
            a column name is already taken.
    """
    values = field.expand(size)
    if names is None:
        names = [field.name + suffix for suffix in _SUFFIXES[field.components]]
    if len(names) != field.components:
        raise ValueError(
            f"field {field.name!r} has {field.components} components, "
            f"expected {len(names)} names"
        )

    for index, name in enumerate(names):
        if name in columns:
            raise ValueError(
                f"column {name!r} from field {field.name!r} already exists"
            )
        column = values if values.ndim == 1 else values[:, index]
        columns[name] = np.ascontiguousarray(column)


def _in_box(lower: Point, upper: Point) -> pl.Expr:
    """Builds a filter for rows whose cell centre lies inside a box.

    Args:
        lower: Lower corner ``(x, y, z)`` of the box.
        upper: Upper corner ``(x, y, z)`` of the box.

    Returns:
        A boolean expression, True for rows inside the box.
    """
    return pl.all_horizontal(
        pl.col(axis).is_between(low, high)
        for axis, low, high in zip("xyz", lower, upper, strict=True)
    )
