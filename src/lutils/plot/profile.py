"""Line plots of field properties, e.g. for comparing several cases.

`plot_profile` draw one line per entry of a mapping from labels to frames.
The frames can come from `FieldData.project_line`, `Sampler.line` or any other
source, such as measured data. With a `CaseManager`, collect them with
`CaseManager.map`::

    profiles = manager.map(
        lambda case: case.field_data(table).project_line(a, b, tol).frame
    )
    plot_profile(profiles, "s", "Ux", labels="velocity")
"""

from collections.abc import Mapping
from typing import Any

from matplotlib.axes import Axes
import polars as pl

from lutils.plot.figure import get_axes
from lutils.plot.labels import AxisLabels
from lutils.plot.labels import resolve_labels

# Column with length in meters
_LENGTH_COLUMNS = frozenset({"x", "y", "z", "s"})


def plot_profile(
    data: Mapping[str, pl.DataFrame],
    x: str,
    y: str,
    *,
    labels: str | AxisLabels | None = None,
    ax: Axes | None = None,
    **line_kwargs: Any,
) -> Axes:
    """Plots one column against another for each entry of ``data``.

    Each entry becomes one line, labelled with its key in the legend. Rows
    are plotted in order of ``x``. Colors, markers and line styles follow
    the active matplotlib style, e.g. ``plt.style.use("lutils.plot.profile")``.

    Args:
        data: Frames by label, e.g. by case label.
        x: Column on the horizontal axis.
        y: Column on the vertical axis.
        labels: A preset name or `AxisLabels`, applied after the defaults.
        ax: Axes to draw on. If None, a new figure is created.
        **line_kwargs: Passed to `matplotlib.axes.Axes.plot` for every line.

    Returns:
        The axes drawn on.

    Raises:
        ValueError: If ``data`` is empty.
        KeyError: If a frame lacks ``x`` or ``y``, or ``labels`` names an
            unknown preset.
    """
    if not data:
        raise ValueError("no data to plot")
    resolved = resolve_labels(labels)
    ax = get_axes(ax)

    for label, frame in data.items():
        missing = [c for c in (x, y) if c not in frame.columns]
        if missing:
            raise KeyError(
                f"{label!r} is missing columns {missing}, "
                f"available: {frame.columns}"
            )
        ordered = frame.select(x, y).sort(x)
        ax.plot(
            ordered.get_column(x).to_numpy(),
            ordered.get_column(y).to_numpy(),
            label=label,
            **line_kwargs,
        )

    ax.set_xlabel(_default_label(x))
    ax.set_ylabel(_default_label(y))
    if resolved is not None:
        resolved.apply(ax)
    ax.legend()

    return ax


def _default_label(column: str) -> str:
    """Builds an axis label from a column name.

    Args:
        column: The column name.

    Returns:
        ``$x$ / m`` for coordinates and ``s``, otherwise the name itself.
    """
    if column in _LENGTH_COLUMNS:
        return f"${column}$ / m"
    return column
