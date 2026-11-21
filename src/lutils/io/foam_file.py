"""Reader for OpenFOAM field files in ASCII and binary format."""

import dataclasses
from pathlib import Path
import re
from typing import Literal, NamedTuple

import numpy as np
from numpy.typing import NDArray

from lutils._typing import StrPath
from lutils.exceptions import FoamParseError
from lutils.io._files import require_file

_COMPONENTS = {
    "scalar": 1,
    "vector": 3,
    "sphericalTensor": 1,
    "symmTensor": 6,
    "tensor": 9,
}

# Mathes the type part of a field class, e.g. Vector in volVectorField
_CLASS_TYPE = re.compile(r"(Scalar|Vector|SphericalTensor|SymmTensor|Tensor)")

_HEADER = re.compile(rb"\bFoamFile\s*\{(.*?)\}", re.DOTALL)
_HEADER_ENTRY = re.compile(rb'(\w+)\s+("[^"]*"|[^;]*);')
_DIMENSIONS = re.compile(rb"\bdimensions\s*\[([^\]]*)\]")
_INTERNAL_FIELD = re.compile(rb"\binternalField\s+(uniform|nonuniform)\s*")
_UNIFORM_VALUE = re.compile(rb"([^;]*);")
_LIST_START = re.compile(rb"List<(\w+)>\s*(\d+)\s*([({])")
_PARENS_TO_SPACES = bytes.maketrans(b"()", b"  ")


class Dimensions(NamedTuple):
    """SI base-unit exponents of an OpenFOAM ``dimensions`` entry.

    The order matches OpenFOAM: ``[kg m s K mol A cd]``. Exponents are floats
    due to OpenFOAM allowing fractional powers.

    Attributes:
        mass: Exponents of kilogram.
        length: Exponent of metre.
        time: Exponents of second.
        temperature: Exponent of kelvin.
        moles: Exponent of mole.
        current: Exponent of current.
        luminous_intensity: Exponent of candela.
    """

    mass: float = 0.0
    length: float = 0.0
    time: float = 0.0
    temperature: float = 0.0
    moles: float = 0.0
    current: float = 0.0
    luminous_intensity: float = 0.0

    @property
    def is_dimensionless(self) -> bool:
        """True if all exponents are zero."""
        return not any(self)


@dataclasses.dataclass(frozen=True, slots=True)
class FoamHeader:
    """Metadata from the ``FoamFile`` dictionary at the top of the file.

    Attributes:
        format: Write format of the data, ``ascii`` or ``binary``.
        field_class: OpenFOAM class name.
        object: Name of the field.
        location: Time directory the file was written to, if recorded.
        label_bytes: Size of an integer label in bytes.
        scalar_bytes: Size of a floating-point scalar in bytes.
        little_endian: True if binary data is stored least significant byte
            first.
    """

    format: Literal["ascii", "binary"]
    field_class: str
    object: str
    location: str | None = None
    label_bytes: int = 4
    scalar_bytes: int = 8
    little_endian: bool = True


@dataclasses.dataclass(frozen=True, slots=True)
class FoamField:
    """The internal field of an OpenFOAM volume field.

    The ``values`` array is read-only.

    Attributes:
        header: Metadata from the ``FoamFile`` dictionary.
        dimensions: SI exponents from the ``dimensions`` entry.
        values: Cell values with shape ``(n,)`` for scalar fields or
            ``(n, components)`` otherwise. For a uniform field, ``n`` is 1.
        is_uniform: True if the file stores a single value for all cells.
    """

    header: FoamHeader
    dimensions: Dimensions
    values: NDArray[np.float64]
    is_uniform: bool

    @property
    def name(self) -> str:
        """The field name from the header."""
        return self.header.object

    @property
    def components(self) -> int:
        """The number of components per cell value."""
        return 1 if self.values.ndim == 1 else self.values.shape[1]

    def expand(self, size: int) -> NDArray[np.float64]:
        """Returns the values for ``size`` cells.

        A uniform field is broadcast to ``size`` cells without copying. A
        nonuniform field is returned unchanged.

        Args:
            size: Number of cells in the mesh.

        Returns:
            A read-only array with ``size`` rows.

        Raises:
            ValueError: If the field is nonuniform and does not have ``size``
                values.
        """
        if self.is_uniform:
            shape = (size,) + self.values.shape[1:]
            return np.broadcast_to(self.values[0], shape)
        if len(self.values) != size:
            raise ValueError(
                f"field {self.name!r} has {len(self.values)} values, "
                f"expected {size}"
            )
        return self.values


def read_field(path: StrPath) -> FoamField:
    """Reads the internal field of an OpenFOAM field file.

    Args:
        path: Path to the field file, e.g. ``case/3000/U``.

    Returns:
        The parsed internal field.

    Raises:
        FileNotFoundError: If the file does not exists.
        FoamParseError: If the file is not a valid OpenFOAM field file or its
            internal field holds an unsupported type.
    """
    file = require_file(path)
    data = file.read_bytes()

    header, position = _parse_header(file, data)

    dimensions = _DIMENSIONS.search(data, position)
    if dimensions is None:
        raise FoamParseError(file, "missing 'dimensions' entry")
    position = dimensions.end()

    internal = _INTERNAL_FIELD.search(data, position)
    if internal is None:
        raise FoamParseError(file, "missing 'internalField' entry")
    position = internal.end()

    if internal.group(1) == b"uniform":
        values = _parse_uniform(file, data, position, header)
        is_uniform = True
    else:
        values, is_uniform = _parse_list(file, data, position, header)

    values.setflags(write=False)
    return FoamField(
        header=header,
        dimensions=_parse_dimensions(file, dimensions.group(1)),
        values=values,
        is_uniform=is_uniform,
    )


def _parse_header(file: Path, data: bytes) -> tuple[FoamHeader, int]:
    """Parses the ``FoamFile`` dictionary.

    Args:
        file: Path of the file.
        data: Full file contents.

    Returns:
        The header and the offset just past its closing brace.

    Raises:
        FoamParseError: If the dictionary is missing or incomplete.
    """
    found = _HEADER.search(data)
    if found is None:
        raise FoamParseError(file, "missing 'FoamFile' header")

    entries = {
        key.decode(): value.decode().strip().strip('"')
        for key, value in _HEADER_ENTRY.findall(found.group(1))
    }

    data_format: Literal["ascii", "binary"]
    match entries.get("format"):
        case "ascii":
            data_format = "ascii"
        case "binary":
            data_format = "binary"
        case other:
            raise FoamParseError(file, f"unsupported format {other!r}")
    for key in ("class", "object"):
        if key not in entries:
            raise FoamParseError(file, f"header is missing {key!r}")

    little_endian, label_bytes, scalar_bytes = _parse_arch(
        entries.get("arch", "")
    )
    header = FoamHeader(
        format=data_format,
        field_class=entries["class"],
        object=entries["object"],
        location=entries.get("location"),
        label_bytes=label_bytes,
        scalar_bytes=scalar_bytes,
        little_endian=little_endian,
    )

    return header, found.end()


def _parse_dimensions(file: Path, text: bytes) -> Dimensions:
    """Parses the body of a ``dimensions [...]`` entry.

    Older files with only the first five exponents are accepted, the missing
    ones are zero.


    Args:
        file: Path of the file.
        text: The text between the brackets.

    Returns:
        The exponents.

    Raises:
        FoamParseError: If the entry does not hold five or seven number.
    """
    try:
        exponents = [float(token) for token in text.split()]
    except ValueError as error:
        raise FoamParseError(
            file, f"dimensions must be numeric, got [{text.decode()}]"
        ) from error

    if len(exponents) not in (5, 7):
        raise FoamParseError(
            file, f"expected 5 or 7 dimensions exponents, got {len(exponents)}"
        )

    return Dimensions(*exponents)


def _parse_arch(arch: str) -> tuple[bool, int, int]:
    """Parses the ``arch`` entry.

    Args:
        arch: Value of the entry without quotes. May be empty, in which case
            the OpenFOAM defaults are returned.

    Returns:
        Whether the data is little-endian, the label size in bytes and the
        scalar size in bytes.
    """
    little_endian, label_bytes, scalar_bytes = True, 4, 8
    for part in arch.split(";"):
        key, _, value = part.strip().partition("=")
        if key in ("LSB", "MSB"):
            little_endian = key == "LSB"
        elif key == "label" and value.isdigit():
            label_bytes = int(value) // 8
        elif key == "scalar" and value.isdigit():
            scalar_bytes = int(value) // 8

    return little_endian, label_bytes, scalar_bytes


def _components_of_class(file: Path, field_class: str) -> int:
    """Finds the number of components from a field class name.

    Args:
        file: Path of the file.
        field_class: Class name.

    Returns:
        The number of components per value.

    Raises:
        FoamParseError: If the class does not name a supported type.
    """
    match = _CLASS_TYPE.search(field_class)
    if match is None:
        raise FoamParseError(file, f"unsupported field class {field_class!r}")
    name = match.group(1)
    return _COMPONENTS[name[0].lower() + name[1:]]


def _parse_uniform(
    file: Path,
    data: bytes,
    position: int,
    header: FoamHeader,
) -> NDArray[np.float64]:
    """Parses ``uniform <value>;``, which is always written as text.

    Args:
        file: Path of the file.
        data: Full file contents.
        positions: Offset just past the ``uniform`` keyword.
        header: The parsed file header.

    Returns:
        An array with one row holding the value.

    Raises:
        FoamParseError: If the value is malformed or does not match the
        field class.
    """
    components = _components_of_class(file, header.field_class)
    match = _UNIFORM_VALUE.match(data, position)
    if match is None:
        raise FoamParseError(file, "unterminated uniform value")

    values = _parse_text(file, match.group(1), 1, components)
    return values.reshape(1, components) if components > 1 else values


def _parse_list(
    file: Path,
    data: bytes,
    position: int,
    header: FoamHeader,
) -> tuple[NDArray[np.float64], bool]:
    """Parses ``nonuniform List<type> n(...)`` or its compact form.

    OpenFOAM writes a list whose items are all equal as ``n{value}``, so
    that form is reported as uniform.

    Args:
        file: Path of the file.
        data: Full file contents.
        position: Offset just past the ``nonuniform`` keyword.
        header: The parsed file header.

    Returns:
        The values and whether the list was written in compact form.

    Raises:
        FoamParseError: If the list is malformed, truncated or holds an
        unsupported type.
    """
    match = _LIST_START.search(data, position)
    if match is None:
        raise FoamParseError(file, "malformed 'nonuniform List' entry")

    type_name = match.group(1).decode()
    if type_name not in _COMPONENTS:
        raise FoamParseError(file, f"unsupported list type {type_name!r}")
    components = _COMPONENTS[type_name]
    size = int(match.group(2))
    is_uniform = match.group(3) == b"{"
    count = 1 if is_uniform else size
    start = match.end()

    if header.format == "binary":
        closing = b"}" if is_uniform else b")"
        values = _parse_binary(file, data, start, count * components, header)
        end = start + values.size * header.scalar_bytes
        if data[end : end + 1] != closing:
            raise FoamParseError(file, "binary list is not closed")
    else:
        end = data.find(b";", start)
        if end == -1:
            raise FoamParseError(file, "unterminated list")
        text = data[start:end].rstrip().removesuffix(b"}").removesuffix(b")")
        values = _parse_text(file, text, count, components)

    if components > 1:
        values = values.reshape(count, components)
    return values, is_uniform


def _parse_text(
    file: Path,
    text: bytes,
    count: int,
    components: int,
) -> NDArray[np.float64]:
    """Parses whitespace-separated numbers, ignoring parentheses.

    Args:
        file: Path of the file.

    Returns:
        A flat array of ``count * components`` values.

    Raises:
        FoamParseError: If a token is not a number or the count is wrong.
    """
    try:
        values = np.array(
            text.translate(_PARENS_TO_SPACES).split(), dtype=np.float64
        )
    except ValueError as error:
        raise FoamParseError(file, str(error)) from error

    expected = count * components
    if values.size != expected:
        raise FoamParseError(
            file, f"expected {expected} values, got {values.size}"
        )

    return values


def _parse_binary(
    file: Path,
    data: bytes,
    start: int,
    count: int,
    header: FoamHeader,
) -> NDArray[np.float64]:
    """Reads raw floating-point values from a binary list.

    Args:
        file: Path of the file.
        data: Full file contents.
        start: Offset of the first byte after the opening bracket.
        count: Number of scalars to read.
        header: The parsed header, giving precision and byte order.

    Returns:
        A flat array of ``count`` values.

    Raises:
        FoamParseError: If the scalar size is not 32 or 64 bits, or the file
            end before ``counts`` values.
    """
    if header.scalar_bytes not in (4, 8):
        raise FoamParseError(
            file, f"unsupported scalar size {header.scalar_bytes * 8} bits"
        )
    order = "<" if header.little_endian else ">"
    dtype = np.dtype(f"{order}f{header.scalar_bytes}")

    if start + count * dtype.itemsize > len(data):
        raise FoamParseError(file, "binary list is truncated")

    values = np.frombuffer(data, dtype=dtype, count=count, offset=start)
    return values.astype(np.float64)
