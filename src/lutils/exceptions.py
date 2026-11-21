"""Exceptions raised by lutils."""

from pathlib import Path

from lutils._typing import StrPath


class LutilsError(Exception):
    """Base class for all lutils errors."""


class CaseNotFoundError(LutilsError):
    """Raised when an OpenFOAM case directory does not exist."""


class FoamParseError(LutilsError):
    """Raised when a file cannot be parsed into the expected structure.

    Attributes:
        path: Path to the file that failed to parse.
        reason: Human-readable description of the problem.
        line: Line number of the offending line, if known.
    """

    def __init__(
        self, path: StrPath, reason: str, line: int | None = None
    ) -> None:
        """Initializes the error.

        Args:
            path: Path to the file that failed to parse.
            reason: Human-readable description of the problem.
            line: Line number of the offending line, if known.
        """
        self.path = Path(path)
        self.reason = reason
        self.line = line
        location = str(self.path) if line is None else f"{self.path}:{line}"
        super().__init__(f"{location}: {reason}")


class ScriptError(LutilsError, RuntimeError):
    """Raised when a script run inside a case exits with an error."""
