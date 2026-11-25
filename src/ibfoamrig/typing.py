"""Type aliases used in the ibfoamrig API."""

import os
from typing import Literal

from numpy.typing import ArrayLike
import polars as pl

__all__ = [
    "Distribution",
    "Method",
    "Point",
    "Points",
    "StrPath",
    "TimeSpec",
]

type StrPath = str | os.PathLike[str]
"""A filesystem path given either as a string or a path-like object."""

type Point = tuple[float, float, float]
"""Spatial coordinates of a cell."""

type Points = ArrayLike | pl.DataFrame
"""Sample points given as an ``(m, 3)`` array, a single point, or a frame
with ``x, y, z`` columns."""

type Distribution = Literal["org", "com"]
"""OpenFOAM distribution, ``"org"`` (Foundation, e.g. v8) or ``"com"``
(ESI, e.g. v2312)."""

type TimeSpec = str | float
"""Time directory given as ``"latest"``, a directory name such as
``"3000"``, or a time value such as ``0.5``."""

type Method = Literal["linear", "nearest", "delaunay"]
"""Interpolation method accepted by the sampling methods."""
