"""Readers that turn OpenFOAM output files into polars frames."""

from lutils.io.tables import read_residuals
from lutils.io.tables import read_table

__all__ = [
    "read_residuals",
    "read_table",
]
