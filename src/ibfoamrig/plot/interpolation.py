"""Plots of the IBM interpolation stencils.

Each boundary cell of an immersed biundary has a line of interpolation
points along the surface normal. These functions show the line geometry in 2D
and 3D.
"""

from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.axes3d import Axes3D
import numpy as np
from numpy.typing import NDArray

from ibfoamrig.core.data import InterpolationData
from ibfoamrig.plot.figure import get_axes

_AXES: tuple[str, str, str] = ("x", "y", "z")
_LINE_COLOR = "0.5"
_LINE_WIDTH = 0.6
_MARKER_SIZE = 12.0


def plot_geometry_2d(
    info: InterpolationData,
    *,
    axes: tuple[str, str] = ("x", "y"),
    ax: Axes | None = None,
    normals: bool = False,
) -> Axes:
    """Plots the interpolation lines projected onto a coordinate plane.

    Each line runs from the boundary cell centre through all interpolation
    points. For 3D cases, select a thin plate first, and choose the plane with
    ``axes``.

    Args:
        info: Interpolation data of the boundary cells to plot.
        axes: The two coordinate axes spanning the plot plane.
        ax: Axes to draw on. If None, a new figure is created.
        normals: If True, draws the surface normal at ``intPoint0`` as an
            arrow, scaled to the spacing of the interpolation points.

    Returns:
        The axes to draw on.

    Raises:
        ValueError: If ``axes`` does not name two different axes.
    """
    indices = _plane_indices(axes)
    lines = _polylines(info)[:, :, indices]
    ax = get_axes(ax)

    ax.add_collection(_line_collection(lines))
    for index, label in enumerate(_point_labels(info)):
        marker, color = _marker(index)
        ax.scatter(
            lines[:, index, 0],
            lines[:, index, 1],
            marker=marker,
            color=color,
            s=_MARKER_SIZE,
            label=label,
        )

    if normals:
        normal = _normals(info)[:, indices]
        length = float(np.median(_spacing(info)))
        ax.quiver(
            lines[:, 1, 0],
            lines[:, 1, 1],
            normal[:, 0] * length,
            normal[:, 1] * length,
            angles="xy",
            scale_units="xy",
            scale=1.0,
            color="tab:red",
            width=0.003,
            label="surface normal",
        )

    ax.set_xlabel(f"${axes[0]}$ / m")
    ax.set_ylabel(f"${axes[1]}$ / m")
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale_view()
    ax.legend()
    return ax


def plot_geometry_3d(
    info: InterpolationData,
    *,
    ax: Axes3D | None = None,
    color_by: str | None = None,
    cmap: str = "viridis",
    points: bool = True,
) -> Axes3D:
    """Plots the interpolation lines in 3D.

    Many lines become unreadable in 3D, consider selecting the boundary cells
    of interest first, e.g. with ``InterpolationData.box``.

    Args:
        info: Interpolation data of the boundary cells to plot.
        ax: 3D axes to draw on. If None, a new figure is created.
        color_by: Column of ``info.frame`` to color the lines by. If None,
            all lines are grey.
        cmap: Colour map used with ``color_by``.
        points: If True, marks the boundary cell centres and interpolation
            points. Turn off for large selections to keep the interactive
            figure smooth and the line colors visible.

    Returns:
        The 3D axes drawn on.

    Raises:
        TypeError: If ``ax`` is not a 3D axes.
        KeyError: If ``color_by`` is not a column of ``info.frame``.
    """
    axes = get_axes(ax, projection="3d")
    if not isinstance(axes, Axes3D):
        raise TypeError("ax must be a 3D axes, create it with projection='3D'")
    lines = _polylines(info)

    collection = Line3DCollection(list(lines), linewidths=0.8)
    if color_by is None:
        collection.set_color(_LINE_COLOR)
    else:
        if color_by not in info.columns:
            raise KeyError(f"no column names {color_by!r} to color by")
        collection.set_array(info.frame.get_column(color_by).to_numpy())
        collection.set_cmap(cmap)
        axes.figure.colorbar(collection, ax=axes, label=color_by, shrink=0.7)
    axes.add_collection3d(collection)

    if points:
        for index, label in enumerate(_point_labels(info)):
            marker, color = _marker(index)
            point = lines[:, index]
            axes.scatter(
                point[:, 0],
                point[:, 1],
                point[:, 2],
                marker=marker,
                color=color,
                s=_MARKER_SIZE,
                label=label,
            )
        axes.legend()

    _set_equal_aspect(axes, lines.reshape(-1, 3))
    axes.set_xlabel("$x$ / m")
    axes.set_ylabel("$y$ / m")
    axes.set_zlabel("$z$ / m")

    return axes


def _line_collection(lines: NDArray[np.float64]) -> LineCollection:
    """Builds the grey collection of interpolation lines or profiles.

    Args:
        lines: Polylines with shape ``(m, p, 2)``.

    Returns:
        The collection, drawn below the markers.
    """
    return LineCollection(
        list(lines), colors=_LINE_COLOR, linewidths=_LINE_WIDTH, zorder=1
    )


def _marker(index: int) -> tuple[str, str]:
    """Returns the marker and colour of a point along an interpolation line.

    Args:
        index: 0 for the boundary cell centre, ``k + 1`` for ``intPointk``.

    Returns:
        The marker style and colour.
    """
    if index == 0:
        return "o", "black"
    return "s", f"C{index - 1}"


def _polylines(info: InterpolationData) -> NDArray[np.float64]:
    """Collects the boundary cell centre and interpolation points per line.

    Args:
        info: Interpolation data.

    Returns:
        Points with shape ``(m, point_count + 1, 3)``. The cell centre firstm
        then ``intPoint0``, ...
    """
    groups = [list(_AXES)] + [
        [f"intPoint{index}_{axis}" for axis in _AXES]
        for index in range(info.point_count)
    ]

    return np.stack(
        [
            np.asarray(info.frame.select(group).to_numpy(), dtype=np.float64)
            for group in groups
        ],
        axis=1,
    )


def _normals(info: InterpolationData) -> NDArray[np.float64]:
    """Returns the unit surface normals with shape ``(m, 3)``."""
    columns = [f"surfNorm_{axis}" for axis in _AXES]
    normal = np.asarray(info.frame.select(columns).to_numpy(), np.float64)
    length = np.linalg.norm(normal, axis=1, keepdims=True)

    return np.asarray(normal / length, dtype=np.float64)


def _spacing(info: InterpolationData) -> NDArray[np.float64]:
    """Returns the distances between consecutive interpolation points."""
    points = _polylines(info)[:, 1:]
    lengths = np.linalg.norm(np.diff(points, axis=1), axis=1)
    return np.asarray(lengths, dtype=np.float64).ravel()


def _point_labels(info: InterpolationData) -> list[str]:
    """Returns legend labels. First the boundary cell, then each point."""
    return ["boundary cell"] + [
        f"intPoint{index}" for index in range(info.point_count)
    ]


def _plane_indices(axes: tuple[str, str]) -> list[int]:
    """Converts two axis names to coordinate indices.

    Args:
        axes: Two different names out of ``x, y, z``.

    Returns:
        The two indices.

    Raises:
        ValueError: If the names are invalid or the same.
    """
    if len(axes) != 2 or len(set(axes)) != 2 or not set(axes) <= set(_AXES):
        raise ValueError(f"axes must be two of {_AXES}, got {axes}")
    return [_AXES.index(axis) for axis in axes]


def _set_equal_aspect(axes: Axes3D, points: NDArray[np.float64]) -> None:
    """Gives all three axes the same scale, so normals are not distorted.

    Args:
        axes: The 3D axes.
        points: All plotted points with shape ``(m, 3)``.
    """
    lower, upper = points.min(axis=0), points.max(axis=0)
    span = upper - lower

    span = np.maximum(span, 1e-3 * span.max())
    centre = (lower + upper) / 2
    axes.set_xlim(centre[0] - span[0] / 2, centre[0] + span[0] / 2)
    axes.set_ylim(centre[1] - span[1] / 2, centre[1] + span[1] / 2)
    axes.set_zlim(centre[2] - span[2] / 2, centre[2] + span[2] / 2)
    axes.set_box_aspect(tuple(span))
