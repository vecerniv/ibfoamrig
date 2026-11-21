"""Placeholder docstring."""

from pathlib import Path


def get_latest_time(case_path: Path) -> int:
    """
    Placeholder
    """

    times = []

    for entry in case_path.iterdir():
        try:
            time = int(entry.name)
        except ValueError:
            continue

        times.append(time)

    return max(times)
