"""Axis labels and titles for common OpenFOAM fields.

Plot functions accept labels either as the name of a preset or as an
`AxisLabels` object, so custom labels need no configuration file.

Presets set only title and the vertical axis label, as the horizontal axis
depends on the plot.
"""

import dataclasses
from types import MappingProxyType
from typing import Final

from matplotlib.axes import Axes


@dataclasses.dataclass(frozen=True, slots=True)
class AxisLabels:
    """Title and axis labels of a plot. None leaves a label unchanged.

    Attributes:
        title: Title of the axes.
        xlabel: Label of the horizontal axis.
        ylabel: Label of the vertical axis.
    """

    title: str | None = None
    xlabel: str | None = None
    ylabel: str | None = None

    def apply(self, ax: Axes) -> None:
        """Sets the labels that are not None on the axes.

        Args:
            ax: Axes to apply the labels to.
        """
        if self.title is not None:
            ax.set_title(self.title)
        if self.xlabel is not None:
            ax.set_xlabel(self.xlabel)
        if self.ylabel is not None:
            ax.set_ylabel(self.ylabel)


PRESETS: Final = MappingProxyType(
    {
        "velocity": AxisLabels(
            title="Velocity profile",
            ylabel=r"$U$ / $\mathrm{m\,s^{-1}}$",
        ),
        "k": AxisLabels(
            title="Turbulence kinetic energy profile",
            ylabel=r"$k$ / $\mathrm{m^{2}\,s^{-2}}$",
        ),
        "nut": AxisLabels(
            title="Turbulence viscosity profile",
            ylabel=r"$\nut_t$ / $\mathrm{m^{2}\,s^{-1}}$",
        ),
        "epsilon": AxisLabels(
            title="Turbulence dissipation rate profile",
            ylabel=r"$\varepsilon$ / $\mathrm{m^{2}\,s^{-3}}$",
        ),
        "omega": AxisLabels(
            title="Specific dissipation rate profile",
            ylabel=r"$\omega$ / $\mathrm{s^{-1}}$",
        ),
        "residuals": AxisLabels(
            title="Residuals",
            xlabel="Time",
            ylabel="Initial residual",
        ),
    }
)
"""Label presets by name. Read-only, adjust a copy with
`dataclass.replace`."""


def resolve_labels(labels: str | AxisLabels | None) -> AxisLabels | None:
    """Turns a preset name into its labels.

    Args:
        labels: A preset name, labels, or None.

    Returns:
        The labels, or None if ``labels`` is None.

    Raises:
        KeyError: If ``labels`` is a name that is not a preset.
    """
    if not isinstance(labels, str):
        return labels
    try:
        return PRESETS[labels]
    except KeyError:
        raise KeyError(
            f"no label preset {labels!r}, available: {list(PRESETS)}"
        ) from None
