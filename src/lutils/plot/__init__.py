"""Plotting functions for lutils data.

Every plot function draws on the given axes (or new ones) and returns them,
so plots can be combined in one figure. `finish_figure` shows and/or saves
the result::

    import matplotlib.pyplot as plt
    from lutils.plot import finish_figure, plot_profile

    plt.style.use("lutils.plot.profile")
    ax = plot_profile(profiles, "s", "Ux", labels="velocity")
    finish_figure(ax.figure, show=True, save="plots/velocity.png")
"""

from lutils.plot.figure import finish_figure
from lutils.plot.interpolation import plot_geometry_2d
from lutils.plot.interpolation import plot_geometry_3d
from lutils.plot.labels import AxisLabels
from lutils.plot.labels import PRESETS
from lutils.plot.profile import plot_profile
from lutils.plot.residuals import plot_residuals

__all__ = [
    "PRESETS",
    "AxisLabels",
    "finish_figure",
    "plot_geometry_2d",
    "plot_geometry_3d",
    "plot_profile",
    "plot_residuals",
]
