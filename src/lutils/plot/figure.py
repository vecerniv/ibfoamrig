"""Figure helpers shared by the plotting modules."""

from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from lutils._typing import StrPath

# Built-in matplotlib backends that only render to files.
_FILE_BACKENDS = frozenset(
    {"agg", "cairo", "pdf", "pgf", "ps", "svg", "template"}
)


def get_axes(ax: Axes | None = None, *, projection: str | None = None) -> Axes:
    """Returns the given axes, or new axes on a new figure.

    Args:
        ax: Axes to draw on. If None, a new figure with one axes is created.
        projection: Projection of new axes, e.g. ``"3d"``. Ignored if ``ax``
            is given.

    Returns:
        The axes to draw on.
    """
    if ax is not None:
        return ax

    figure = plt.figure()
    return figure.add_subplot(projection=projection)


def finish_figure(
    figure: Figure,
    *,
    show: bool = False,
    save: StrPath | None = None,
    close: bool = True,
    **savefig_kwargs: Any,
) -> Path | None:
    """Shows and/or saves a figure, then closes it.

    If both ``show`` and ``save`` are set, the figure is saved after the window
    is closed, keeping the view rotated or zoomed to.

    Args:
        figure: The figure to finish. To be shown, it must be managed by
            pyplot.
        show: If True, opens an interactive window and blocks until it is
            closed. Shows any other open pyplot figures.
        save: Output file. Missing parent directories are created. If None
            nothing is saved.
        close: If True, the figure is closed after saving to free memory.
        **kwargs: Passed to `matplotlib.figure.Figure.savefig`.

    Returns:
        The path the figure was saved to, or None if it was now saved.

    Raises:
        RuntimeError: If ``show`` is True but the active matplotlib backend
            cannot open windows.
        ValueError: If ``show`` is True but the figure is not managed by
            pyplot.
    """
    if show:
        _require_interactive(figure)
        plt.show()

    output = None
    if save is not None:
        output = Path(save)
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, **savefig_kwargs)

    if close:
        plt.close(figure)

    return output


def _require_interactive(figure: Figure) -> None:
    """Checks that a figure can be shown in a windows.

    Args:
        figure: The figure to show.

    Raises:
        RuntimeError: If the active matplotlib backend cannot open windows.
        ValueError: If the figure is not managed by pyplot.
    """
    backend = matplotlib.get_backend()
    if backend.lower() in _FILE_BACKENDS:
        raise RuntimeError(
            f"matplotlib backend {backend!r} cannot open windows, "
            f"install GUI toolkit or set MPLBACKEND"
        )

    if figure.canvas.manager is None:
        raise ValueError(
            "figure is not manged by pyplot, create it with "
            "plt.figure() or plt.subplots() to show it"
        )
