"""Reader for STL surface files in ASCII and binary format.

STL files describe a surface as a list of triangles. The face normals stored
in the file are ignored, only the vertices are read.
"""

from pathlib import Path
import re

import numpy as np
from numpy.typing import NDArray

from ibfoamrig.exceptions import FoamParseError
from ibfoamrig.io._files import require_file
from ibfoamrig.typing import StrPath

# Bindary STL: 80-byte header, uint32 triangle count, 50 bytes per triangle
_HEADER_BYTES = 80
_COUNT_BYTES = 4
_TRIANGLE_DTYPE = np.dtype(
    [
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attributes", "<u2"),
    ]
)
_VERTEX = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def read_stl(path: StrPath) -> NDArray[np.float64]:
    """Reads the triangles of an STL file.

    The format is detected from the file size. A file whose size matches
    the triangle count in a binary header is read as binary, anything else
    as ASCII.

    Args:
        path: Path to the STL.

    Returns:
        Vertex coordinates with shape ``(n, 3, 3)``. ``n`` triangles of three
        vertices with ``x, y, z`` each.

    Raises:
        FileNotFoundError: If the file does not exist.
        FoamParseError: If the file holds no triangles or a malformed vertex.
    """
    file = require_file(path)
    data = file.read_bytes()

    if _is_binary(data):
        triangles = _read_binary(data)
    else:
        triangles = _read_ascii(file, data)

    if len(triangles) == 0:
        raise FoamParseError(file, "no triangles found")
    return triangles


def _is_binary(data: bytes) -> bool:
    """Checks whether STL data has the size of a binary file.

    Args:
        data: Full file contents.

    Returns:
        True if the triangle count in the header matches the file size.
    """
    start = _HEADER_BYTES + _COUNT_BYTES
    if len(data) < start:
        return False
    count = int.from_bytes(data[_HEADER_BYTES:start], "little")
    return len(data) == start + count * _TRIANGLE_DTYPE.itemsize


def _read_binary(data: bytes) -> NDArray[np.float64]:
    """Reads the triangles of a binary STL file.

    Args:
        data: Full file contents.

    Returns:
        Vertex coordinates with shape ``(n, 3, 3)``.
    """
    records = np.frombuffer(
        data, dtype=_TRIANGLE_DTYPE, offset=_HEADER_BYTES + _COUNT_BYTES
    )
    return records["vertices"].astype(np.float64)


def _read_ascii(file: Path, data: bytes) -> NDArray[np.float64]:
    """Reads the triangles of an ASCII STL file.

    Args:
        file: Path of the file.
        data: Full file contents.

    Returns:
        Vertex coordinates with shape ``(n, 3, 3)``.

    Raises:
        FoamParseError: If a vertex is not numeric or the vertex count is
            not a multiple of three.
    """
    try:
        vertices = np.array(_VERTEX.findall(data), dtype=np.float64)
    except ValueError as error:
        raise FoamParseError(file, f"malformed vertex: {error}") from error

    if len(vertices) % 3:
        raise FoamParseError(
            file, f"{len(vertices)} do not form whole triangles"
        )

    return vertices.reshape((-1, 3, 3))
