"""Internal helpers shared by the io readers."""

from pathlib import Path

from lutils._typing import StrPath


def require_file(path: StrPath) -> Path:
    """Checks that a path points to an existing regular file.

    Args:
        path: Path to check.

    Returns:
        The path converted to a `pathlib.Path`.

    Raises:
        FileNotFoundError: If a path does not exist or is not a file.
    """
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")
    return target
