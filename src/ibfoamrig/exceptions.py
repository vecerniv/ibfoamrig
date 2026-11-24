"""Exceptions raised by ibfoamrig."""

from pathlib import Path

from ibfoamrig._typing import StrPath


class IbfoamrigError(Exception):
    """Base class for all ibfoamrig errors."""


class CaseNotFoundError(IbfoamrigError):
    """Raised when an OpenFOAM case directory does not exist."""


class FoamParseError(IbfoamrigError):
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


class ScriptError(IbfoamrigError, RuntimeError):
    """Raised when a script run inside a case exits with an error."""


class TimeNotFoundError(IbfoamrigError, LookupError):
    """Raised when a case has no time directory matching a request."""
