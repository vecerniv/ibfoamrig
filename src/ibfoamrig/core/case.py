"""Access to the files of a single OpenFOAM case.

`FoamCase` knows where things live inside a case directory and returns the
ibfoamrig containers for them. It is stateless, every method reads from disk and
returns a new object.
"""

import dataclasses
from pathlib import Path
import subprocess
from typing import NamedTuple

import numpy as np
import polars as pl

from ibfoamrig.core import time_dirs
from ibfoamrig.core.data import FieldData
from ibfoamrig.core.data import InterpolationData
from ibfoamrig.core.data import ResidualData
from ibfoamrig.core.time_dirs import TimeDirectory
from ibfoamrig.exceptions import CaseNotFoundError
from ibfoamrig.exceptions import ScriptError
from ibfoamrig.io import foam_file
from ibfoamrig.io import tables
from ibfoamrig.typing import Distribution
from ibfoamrig.typing import StrPath
from ibfoamrig.typing import TimeSpec


class FieldStats(NamedTuple):
    """Summary statistics of a field over a subset of cells.

    Attributes:
        cells: Number of cells included.
        mean: Arithemtic mean of the values.
        min: Smallest value.
        max: Largest value.
    """

    cells: int
    mean: float
    min: float
    max: float


@dataclasses.dataclass(frozen=True, slots=True)
class FoamCase:
    """An OpenFOAM case directory.

    Attributes:
        path: Path to the case directory.
        label: Name of the case in plots and messages. Defaults to the name
            of the case directory.
        distribution: OpenFOAM distribution that ran the case.
    """

    path: Path
    label: str = ""
    distribution: Distribution = "org"

    def __post_init__(self) -> None:
        """Normalises the path and label and checks the case exists.

        Raises:
            CaseNotFoundError: If ``path`` is not a directory.
        """
        path = Path(self.path)
        if not path.is_dir():
            raise CaseNotFoundError(f"case not found: {path}")
        # class is frozen, fields set through object
        object.__setattr__(self, "path", path)
        if not self.label:
            object.__setattr__(self, "label", path.resolve().name)

    def times(self, *, no_zero: bool = False) -> list[TimeDirectory]:
        """Lists the time directories in ascending order.

        Args:
            no_zero: If True, the zero time directory is left out.

        Returns:
            The time directories, empty if there are none.
        """
        return time_dirs.list_times(self.path, no_zero=no_zero)

    def time(self, time: TimeSpec = "latest") -> TimeDirectory:
        """Finds a time directory.

        Args:
            time: ``"latest"``, a directory name or a time value.

        Returns:
            The matching time directory.

        Raises:
            TimeNotFoundError: If no time directory matches.
        """
        if time == "latest":
            return time_dirs.latest_time(self.path)
        return time_dirs.find_time(self.path, time)

    def read_field(
        self, name: str, time: TimeSpec = "latest"
    ) -> foam_file.FoamField:
        """Reads a field file from a time directory.

        Args:
            name: Field name.
            time: The time directory, see `time`.

        Returns:
            The internal field.

        Raises:
            TimeNotFoundError: If the time directory does not exist.
            FileNotFoundError: If the field file does not exist.
            FoamParseError: If the file cannot be parsed.
        """
        return foam_file.read_field(self.time(time).path / name)

    def fields_at(
        self,
        names: list[str],
        time: TimeSpec = "latest",
        *,
        centres: str = "C",
        volumes: str | None = "V",
    ) -> FieldData:
        """Builds field data from the field files of a time directory.

        The cell centres come from the ``C`` field, written by
        ``postProcess -func writeCellCentres``. Cell volumes are added if a
        ``V`` field exists.

        Args:
            names: Fields to include.
            time: The time directory, see `time`.
            centres: Name of the cell-centre field.
            volumes: Name of the cell-volume field, or None to skip it.

        Returns:
            The field data, with cells in mesh order.

        Raises:
            TimeNotFoundError: If the time directory does not exist.
            FileNotFoundError: If the cell centres or a field are missing.
            ValueError: If a field does not match the number of cells.
        """
        directory = self.time(time)
        if not (directory.path / centres).is_file():
            raise FileNotFoundError(
                f"no cell centres {centres!r} in {directory.path}, write "
                f"them with `postProcess -func writeCellCentres -time "
                f"{directory.name}`"
            )

        volume_field = None
        if volumes is not None and (directory.path / volumes).is_file():
            volume_field = self.read_field(volumes, directory.name)

        return FieldData.from_fields(
            self.read_field(centres, directory.name),
            [self.read_field(name, directory.name) for name in names],
            volumes=volume_field,
        )

    def field_data(
        self, table: StrPath, *, fields: list[str] | None = None
    ) -> FieldData:
        """Loads a table written by a function object.

        Args:
            table: Path to the table, relative to the case directory.
            fields: Field columns to keep. If None, all are loaded.

        Returns:
            The loaded field data.

        Raises:
            FileNotFoundError: If the table does not exist.
            FoamParseError: If a requested column is missing.
        """
        return FieldData.from_file(self.path / table, fields=fields)

    def residuals(self, function: str = "residuals") -> ResidualData:
        """Loads the residuals written by the residuals function object.

        A restarted run writes one ``residuals.dat`` per start time. They are
        joined in time order. Where runs overlap, the later run is kept.

        Args:
            function: Name of the function object.

        Returns:
            The residuals of the whole run.

        Raises:
            NotImplementedError: For ``"com"`` cases, whose output format is
                not supported yet.
            FileNotFoundError: If no residual file exists.
            FoamParseError: If a file is malformed.
        """
        if self.distribution != "org":
            raise NotImplementedError(
                f"residuals of {self.distribution!r} cases are not supported"
            )

        root = self.path / "postProcessing" / function
        files = [
            entry.path / "residuals.dat"
            for entry in _times_or_empty(root)
            if (entry.path / "residuals.dat").is_file()
        ]
        if not files:
            raise FileNotFoundError(f"no rediduals.dat found under {root}")

        frames = [tables.read_residuals(file) for file in files]
        # Drop rows that are overwritten by a later time
        for index, later in enumerate(frames[1:]):
            if not later.is_empty():
                start = later.get_column("Time")[0]
                frames[index] = frames[index].filter(pl.col("Time") < start)

        return ResidualData(frame=pl.concat(frames, how="diagonal_relaxed"))

    def interpolation(
        self, table: StrPath, cells: FieldData
    ) -> InterpolationData:
        """Loads IBM interpolation info and joins the cell centres.

        Args:
            table: Path to the interpolation info, relative to the case
                directory.
            cells: Field data of this case providing the cell centres.

        Returns:
            The interpolation data, one row per boundary cell.

        Raises:
            FileNotFoundError: If the table does not exist.
            ValueError: If a boundary cell is missing from ``cells``.
        """
        return InterpolationData.from_file(self.path / table, cells)

    def boundary_stats(
        self, field: str = "yPlusi", time: TimeSpec = "latest"
    ) -> FieldStats:
        """Summarises a field over the IBM boundary cells.

        The solver writes boundary fields such as with a positive values
        in boundary cells and zero or ``-1`` elsewhere, so only positive
        values are included.

        Args:
            field: Name of the field.
            time: The time directory, see `time`.

        Returns:
            Cell count, mean, minimum and maximum over the boundary cells.

        Raises:
            TimeNotFoundError: If the time directory does not exist.
            FileNotFoundError: If the field file does not exist.
            ValueError: If the field is not a scalar or has no positive
                values.
        """
        values = self.read_field(field, time).values
        if values.ndim != 1:
            raise ValueError(f"field {field!r} is not a scalar field")
        boundary = values[values > 0]

        if boundary.size == 0:
            raise ValueError(f"field {field!r} has no positive values")

        return FieldStats(
            cells=int(boundary.size),
            mean=float(np.mean(boundary)),
            min=float(np.min(boundary)),
            max=float(np.max(boundary)),
        )

    def run(self, script: StrPath, *args: str) -> None:
        """Runs a script with the case directory as working directory.

        The script's output does to the terminal as usual.

        Args:
            script: Path to an executable script. A relative path is resolved
                against the case directory, e.g. ``"Allrun"``.

        Raises:
            FileNotFoundError: If the script does not exist.
            ScriptError: If the script cannot be started ot exits with a
                non-zero code.
        """
        executable = self.path / script
        if not executable.is_file():
            raise FileNotFoundError(f"script not found: {executable}")
        try:
            subprocess.run(
                [str(executable.resolve()), *args], cwd=self.path, check=True
            )
        except subprocess.CalledProcessError as error:
            raise ScriptError(
                f"{executable.name} failed in case {self.label!r} with exit "
                f"code {error.returncode}"
            ) from error
        except OSError as error:
            raise ScriptError(
                f"cannot run {executable} in case {self.label!r}: {error}"
            ) from error


def _times_or_empty(root: Path) -> list[TimeDirectory]:
    """Lists the time directories of ``root``, or none if it is missing."""
    if not root.is_dir():
        return []
    return time_dirs.list_times(root)
