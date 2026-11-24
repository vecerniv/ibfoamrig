"""Readers for tabular OpenFOAM post-processing output.

Supports two formats:

* Comma-separated tables with a header row, as written by the
  ``readAndWrite*`` applications.
* Tab-separated residual files written by the ``residuals`` function object.
"""

from collections.abc import Sequence

import polars as pl

from ibfoamrig._typing import StrPath
from ibfoamrig.exceptions import FoamParseError
from ibfoamrig.io._files import require_file

_COMMENT = "#"
_NOT_AVAILABLE = "N/A"


def read_table(
    path: StrPath,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Read a comma-separated post-processing table.

    The file is scanned lazily, selecting a subset of ``columns`` avoids
    parsing the rest of the file.

    Args:
        path: Path to the table file.
        columns: Names of the columns to keep, in the order given. If None,
            all columns are returned.

    Returns:
        The table with column types inferred by polars.

    Raises:
        FileNotFoundError: If a file does not exist.
        FoamParseError: If any of the requested columns is missing.
    """
    file = require_file(path)
    frame = pl.scan_csv(file)

    if columns is not None:
        available = frame.collect_schema().names()
        missing = [name for name in columns if name not in available]
        if missing:
            raise FoamParseError(
                file, f"Missing columns {missing}. Available: {available}"
            )
        frame = frame.select(columns)

    return frame.collect()


def read_residuals(path: StrPath) -> pl.DataFrame:
    """Reads a residuals file written by the OpenFOAM residuals function object.

    Args:
        path: Path to the ``residuals.dat`` file.

    Returns:
        A frame with a ``Time`` column followed by one column per residual,
        all of type ``Float64``.

    Raises:
        FileNotFoundError: If the file does not exist.
        FoamParseError: If the header is missing, or a row is longer than the
            header or holds a value that is not a number.
    """
    file = require_file(path)
    names: list[str] | None = None
    rows: list[list[float | None]] = []

    with file.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line.startswith(_COMMENT):
                header = line.lstrip(_COMMENT).split()
                if header:
                    names = header
                continue

            fields = [field.strip() for field in line.split("\t")]
            if fields == [""]:
                continue
            if names is None:
                raise FoamParseError(file, "data before header", line_number)
            if len(fields) > len(header):
                raise FoamParseError(
                    file,
                    f"expected {len(names)} values, got {len(fields)}",
                    line_number,
                )
            if len(fields) < len(names):
                continue

            try:
                rows.append([_to_float(field) for field in fields])
            except ValueError as error:
                raise FoamParseError(file, str(error), line_number) from error

    if names is None:
        raise FoamParseError(file, "no header found")

    return pl.DataFrame(
        rows,
        schema={name: pl.Float64 for name in names},
        orient="row",
    )


def _to_float(field: str) -> float | None:
    """Converts one residual value, mapping ``N/A`` to None.

    Args:
        field: The stripped text of the value.

    Returns:
        The value as a float, or None if it is ``N/A``.

    Raises:
        ValueError: If the text is neither a number not ``N/A``.
    """
    if field == _NOT_AVAILABLE:
        return None
    return float(field)
