"""Readers that turn OpenFOAM output files into arrays and polars frames."""

from ibfoamrig.io.foam_file import Dimensions
from ibfoamrig.io.foam_file import FoamField
from ibfoamrig.io.foam_file import FoamHeader
from ibfoamrig.io.foam_file import read_field
from ibfoamrig.io.stl import read_stl
from ibfoamrig.io.tables import read_residuals
from ibfoamrig.io.tables import read_table

__all__ = [
    "Dimensions",
    "FoamField",
    "FoamHeader",
    "read_field",
    "read_residuals",
    "read_stl",
    "read_table",
]
