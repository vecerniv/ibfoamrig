"""Plotting functions for ibfoamrig data.

Every plot function draws on the given axes (or new ones) and returns them,
so plots can be combined in one figure. `finish_figure` shows and/or saves
the result::

    import matplotlib.pyplot as plt
    from ibfoamrig.plot import finish_figure, plot_profile

    plt.style.use("ibfoamrig.plot.profile")
    ax = plot_profile(profiles, "s", "Ux", labels="velocity")
    finish_figure(ax.figure, show=True, save="plots/velocity.png")
"""

from ibfoamrig.plot.figure import finish_figure
from ibfoamrig.plot.interpolation import plot_geometry_2d
from ibfoamrig.plot.interpolation import plot_geometry_3d
from ibfoamrig.plot.labels import AxisLabels
from ibfoamrig.plot.labels import PRESETS
from ibfoamrig.plot.profile import plot_profile
from ibfoamrig.plot.residuals import plot_residuals

__all__ = [
    "PRESETS",
    "AxisLabels",
    "finish_figure",
    "plot_geometry_2d",
    "plot_geometry_3d",
    "plot_profile",
    "plot_residuals",
]
