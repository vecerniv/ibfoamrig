"""Convergence plots of solver residuals."""

from collections.abc import Sequence

from matplotlib.axes import Axes
import numpy as np

from lutils.core.data import ResidualData
from lutils.plot.figure import get_axes
from lutils.plot.labels import AxisLabels
from lutils.plot.labels import resolve_labels


def plot_residuals(
    residuals: ResidualData,
    *,
    fields: Sequence[str] | None = None,
    labels: str | AxisLabels | None = "residuals",
    ax: Axes | None = None,
) -> Axes:
    """Plots residuals against time on logarithmic scale.

    Each residual column becomes one line. Values that were not solved
    and non-positive values leave gaps instead of dropping to zero.

    Args:
        residuals: The residuals to plot.
        fields: Residual columns to plot. If None, all residuals are plotted.
        labels: A preset name or `AxisLabels`. Defaults to the ``"residuals"``
            preset.
        ax: Axes to draw on. If None, a new figure is created.

    Returns:
        The axes drawn on.

    Raises:
        TypeError: If ``fields`` is a single string.
        KeyError: If a field is not a residual column, or ``labels`` names
            an unknown preset.
        ValueError: If no fields are selected.
    """
    if isinstance(fields, str):
        raise TypeError("fields must be a sequence of names, not a single str")

    names = residuals.fields if fields is None else list(fields)
    if not names:
        raise ValueError("no residuals to plot")

    missing = [name for name in names if name not in residuals.fields]
    if missing:
        raise KeyError(f"no residuals {missing}, available: {residuals.fields}")
    resolved = resolve_labels(labels)
    ax = get_axes(ax)

    time = residuals.frame.get_column("Time").to_numpy()
    for name in names:
        values = residuals.frame.get_column(name).to_numpy().astype(np.float64)
        # Masks non-positive values to avoid spikes in log-scale plot
        values[values <= 0] = np.nan
        ax.plot(time, values, label=name)

    ax.set_yscale("log")
    ax.set_xlabel("Time")
    if resolved is not None:
        resolved.apply(ax)
    ax.legend()

    return ax
