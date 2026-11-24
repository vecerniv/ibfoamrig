"""Discovery of OpenFOAM time directories."""

import dataclasses
import math
from operator import attrgetter
from pathlib import Path
import re

from ibfoamrig._typing import StrPath
from ibfoamrig.exceptions import CaseNotFoundError
from ibfoamrig.exceptions import TimeNotFoundError

# Plain or scientific decimal regex pattern
_TIME_NAME = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


@dataclasses.dataclass(frozen=True, slots=True)
class TimeDirectory:
    """A time directory of an OpenFOAM case.

    Attributes:
        name: Directory name as written by OpenFOAM.
        value: The time as a number.
        path: Path to the directory.
    """

    name: str
    value: float
    path: Path


def list_times(
    case_path: StrPath,
    *,
    no_zero: bool = False,
) -> list[TimeDirectory]:
    """Lists the time directory of a case in ascending order.

    Args:
        case_path: Path to the case directory.
        no_zero: If True, the zero time directory is left out.

    Returns:
        The time directories sorted by time. Empty if there are none.

    Raises:
        CaseNotFoundError: If ``case_path`` is not a directory.
    """
    root = Path(case_path)
    if not root.is_dir():
        raise CaseNotFoundError(f"Case not found: {root}")

    times = []
    for entry in root.iterdir():
        if not entry.is_dir() or _TIME_NAME.fullmatch(entry.name) is None:
            continue
        value = float(entry.name)
        if no_zero and value == 0:
            continue
        times.append(TimeDirectory(name=entry.name, value=value, path=entry))

    return sorted(times, key=attrgetter("value"))


def latest_time(
    case_path: StrPath,
    *,
    no_zero: bool = True,
) -> TimeDirectory:
    """Finds the latest time directory of a case.

    Args:
        case_path: Path to the case directory.
        no_zero: If True, the zero time directory is left out. A case that has
            not been run raises an error.

    Returns:
        The most recent time directory.

    Raises:
        CaseNotFoundError: If ``case_path`` is not a directory.
        TimeNotFoundError: If the case has no matching time directory.
    """
    times = list_times(case_path, no_zero=no_zero)
    if not times:
        raise TimeNotFoundError(f"No time directories found in {case_path}")

    return times[-1]


def find_time(case_path: StrPath, time: str | float) -> TimeDirectory:
    """Finds the time directory for a given time.

    A string is matched against the dictionary names exactly. A number is
    matched by value with a relative tolerance.

    Args:
        case_path: Path to the case directory.
        time: Directory name or time value to look for.

    Returns:
        The matching time directory.

    Raises:
        CaseNotFoundError: If ``case_path`` is not a directory.
        TimeNotFoundError: If no time directory matches ``time``.
    """
    for entry in list_times(case_path):
        if isinstance(time, str):
            if entry.name == time:
                return entry
        elif math.isclose(entry.value, time, rel_tol=1e-9, abs_tol=1e-12):
            return entry
    raise TimeoutError(f"Time {time!r} not found in {case_path}")
