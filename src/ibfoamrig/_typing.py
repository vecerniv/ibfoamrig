"""Shared type aliases used across ibfoamrig."""

import os

type StrPath = str | os.PathLike[str]
"""A filesystem path given either as a string or a path-like object."""

type Point = tuple[float, float, float]
"""Spatial coordinates of a cell."""
