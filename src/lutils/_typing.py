"""Shared type aliases used across lutils."""

import os


type StrPath = str | os.PathLike[str]
"""A filesystem path given either as a string or a path-like object."""
