"""A labelled collection of OpenFOAM case.

`CaseManager` is read-only mapping from case labels to `FoamCase` objects.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import Self

from ibfoamrig._typing import StrPath
from ibfoamrig.core.case import Distribution
from ibfoamrig.core.case import FoamCase


class CaseManager(Mapping[str, FoamCase]):
    """A read-only mapping from case labels to cases, in insertion order."""

    __slots__ = ("_cases",)

    def __init__(self, cases: Iterable[FoamCase] = ()) -> None:
        """Collects cases under their labels.

        Args:
            cases: The cases to manage. Their labels must be unique.

        Raises:
            ValueError: If two cases share a label.
        """
        self._cases: dict[str, FoamCase] = {}
        for case in cases:
            if case.label in self._cases:
                raise ValueError(f"duplicate case label {case.label!r}")
            self._cases[case.label] = case

    @classmethod
    def from_paths(
        cls,
        paths: Mapping[str, StrPath],
        *,
        distribution: Distribution = "org",
    ) -> Self:
        """Creates cases from mapping of labels to case directories.

        Args:
            paths: Case directories by label.
            distribution: OpenFOAM distribution of all cases.

        Returns:
            The manager holding one case per entry.

        Raises:
            CaseNotFoundError: If a path is not a directory.
        """
        return cls(
            FoamCase(Path(path), label, distribution)
            for label, path in paths.items()
        )

    def __getitem__(self, label: str) -> FoamCase:
        """Returns the case with the given label.

        Args:
            label: The case label.

        Returns:
            The case.

        Raises:
            keyError: If no case has this label.
        """
        try:
            return self._cases[label]
        except KeyError:
            raise KeyError(
                f"no case {label!r}, available: {list(self._cases)}"
            ) from None

    def __iter__(self) -> Iterator[str]:
        """Iterates over the case labels in insertion order."""
        return iter(self._cases)

    def __len__(self) -> int:
        """Returns the number of cases."""
        return len(self._cases)

    def __repr__(self) -> str:
        """Returns a short description listing the case labels."""
        return f"{type(self).__name__}({list(self._cases)})"

    def select(self, labels: Iterable[str]) -> Self:
        """Returns a manager holding only some of the cases.

        Args:
            labels: Labels of the cases to keep, in order to keep them.

        Returns:
            A new manager with the selected cases.

        Raises:
            KeyError: If a label does not exist.
            ValueError: If a label is repeated.
        """
        return type(self)(self[label] for label in labels)

    def run(
        self,
        script: StrPath,
        *args: str,
        labels: Iterable[str] | None = None,
    ) -> None:
        """Runs a script in each case, one after another.

        Stops at the first case whose script fails.

        Args:
            script: Path to the script, a relative path is resolved against
                each case directory, see `FoamCase.run`.
            *args: Command-line arguments passed to the script.
            labels: Labels of the cases to run in, in order. If None, all
                cases are used.

        Raises:
            KeyError: If a label does not exist.
            FileNotFoundError: If the script is missing in a case.
            ScriptError: If the script fails, the message names the case.
        """
        cases = self if labels is None else self.select(labels)
        for case in cases.values():
            case.run(script, *args)

    def map[T](
        self,
        function: Callable[[FoamCase], T],
        *,
        labels: Iterable[str] | None = None,
    ) -> dict[str, T]:
        """Applies a function to each case, keyed by case label.

        Typical use is collecting data from all cases for one plot::

            def profile(case: FoamCase) -> pl.DataFrame:
                cells = case.field_data(table)
                return cells.project_line(start, end, tol).frame

            profiles = manager.map(profile)

        Args:
            function: Called with each case, its result is stored under the
                case label.
            labels:
                Labels of the cases to use, in order. If None, all cases are
                    used.

        Returns:
            The results by case label, in case order.

        Raises:
            KeyError: If a label does not exist.
            Exception: Any exception raised by ``function``, with a note
                naming the case it failed for.
        """
        cases = self if labels is None else self.select(labels)
        results: dict[str, T] = {}
        for label, case in cases.items():
            try:
                results[label] = function(case)
            except Exception as error:
                error.add_note(f"while processing case {label!r}")
                raise

        return results
