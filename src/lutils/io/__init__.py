"""Readers that turn OpenFOAM output files into arrays and polars frames."""

from lutils.io.foam_file import Dimensions
from lutils.io.foam_file import FoamField
from lutils.io.foam_file import FoamHeader
from lutils.io.foam_file import read_field
from lutils.io.tables import read_residuals
from lutils.io.tables import read_table

__all__ = [
    "Dimensions",
    "FoamField",
    "FoamHeader",
    "read_field",
    "read_residuals",
    "read_table",
]
