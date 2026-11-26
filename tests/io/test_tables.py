"""Tests for the `ibfoamrig.io.tables` readers."""

from collections.abc import Callable
from pathlib import Path

import polars as pl
import pytest

from ibfoamrig.exceptions import FoamParseError
from ibfoamrig.io.tables import read_residuals
from ibfoamrig.io.tables import read_table

RESIDUAL_COLUMNS = ["Time", "Ux", "Uy", "p"]
HEADER = "# Residuals\n# Time\tUx\tUy\tp\n"


def _write(directory: Path, text: str, name: str = "file.dat") -> Path:
    """Writes ``text`` to a file in ``directory`` and returns its path."""
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(name="boundary_info")
def fixture_boundary_info(data_dir: Path) -> Path:
    """Returns the 2D interpolation info table of the HFDIB-RANS case."""
    folder = data_dir / "2d_hfdibrans" / "ZZ_python"
    return folder / "interpolationInfo_boundary.dat"


class TestReadTable:
    """Tests for `read_talbe`."""

    def test_reads_all_columns(self, boundary_info: Path) -> None:
        """Tests that a table is read whole, with inffered column type."""
        frame = read_table(boundary_info)

        assert frame.shape == (28, 18)
        assert frame.columns[:4] == [
            "cellI",
            "surfNorm_x",
            "surfNorm_y",
            "surfNorm_z",
        ]
        assert frame.schema["cellI"] == pl.Int64
        assert frame.schema["surfNorm_x"] == pl.Float64
        assert frame["cellI"][0] == 88
        assert frame["surfNorm_x"][0] == -0.2840152073

    def test_selects_columns_in_given_order(self, boundary_info: Path) -> None:
        """Tests that ``columns`` picks a subset in the requested order."""
        frame = read_table(boundary_info, columns=["sigma", "cellI"])

        assert frame.columns == ["sigma", "cellI"]
        assert frame.height == 28

    def test_missing_columns_raises(self, boundary_info: Path) -> None:
        """Tests that requesting an absent column raises it in the error."""
        with pytest.raises(FoamParseError) as error:
            read_table(boundary_info, columns=["cellI", "nuh-uh"])

        assert error.value.path == boundary_info
        assert "['nuh-uh']" in error.value.reason
        assert error.value.line is None

    @pytest.mark.parametrize("convert", [str, Path], ids=["str", "Path"])
    def test_accepts_str_and_path(
        self, tmp_path: Path, convert: Callable[[Path], str | Path]
    ) -> None:
        """Tests that the path may be given as a string or a path object."""
        path = _write(tmp_path, "a,b\n1,2.5\n")

        frame = read_table(convert(path))

        assert frame.to_dict(as_series=False) == {"a": [1], "b": [2.5]}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Tests that a path to nothing raises `FileNotFoundError`."""
        with pytest.raises(FileNotFoundError):
            read_table(tmp_path / "missing.dat")

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_table(tmp_path)


class TestReadResidualCases:
    """Tests for `read_residuals` on the residuals of the test cases."""

    @pytest.mark.parametrize("case", ["2d_simple", "2d_hfdibrans"])
    @pytest.mark.parametrize("start", [0, 5])
    def test_reads_residuls(
        self, data_dir: Path, case: str, start: int
    ) -> None:
        """Tests the columns, types and times of a solver residual file.

        The first row of each run holds fewer values than the header and is
        skipped. The times start one step after the start time.
        """
        path = data_dir / case / "postProcessing" / "residuals" / str(start)

        frame = read_residuals(path / "residuals.dat")

        assert frame.columns == RESIDUAL_COLUMNS
        assert all(dtype == pl.Float64 for dtype in frame.dtypes)
        assert frame["Time"].to_list() == [start + i for i in range(1, 6)]
        assert frame.null_count().row(0) == (0, 0, 0, 0)

    def test_reads_values(self, data_dir: Path) -> None:
        """Tests that the residual values are parsed exactly."""
        path = data_dir / "2d_simple" / "postProcessing" / "residuals" / "0"

        frame = read_residuals(path / "residuals.dat")

        assert frame.row(0) == (1.0, 1.0, 1.0, 1.0)
        assert frame.row(-1) == (
            5.0,
            7.4472948055e-02,
            1.0362642503e-01,
            3.5702708594e-02,
        )


class TestReadResiduals:
    """Tests for `read_residuals` on handwritten files."""

    def test_not_available_is_null(self, tmp_path: Path) -> None:
        """Tests that ``N/A`` in a full row becomes a null value."""
        path = _write(tmp_path, HEADER + "1\tN/A\t0.5\t0.25\n")

        frame = read_residuals(path)

        assert frame.row(0) == (1.0, None, 0.5, 0.25)
        assert frame.schema["Ux"] == pl.Float64

    def test_skips_short_and_blank_lines(self, tmp_path: Path) -> None:
        """Tests that incomplete rows and empty lines are left out."""
        text = HEADER + "0\tN/A\tN/A\n\n   \n1\t0.1\t0.2\t0.3\n"
        path = _write(tmp_path, text)

        frame = read_residuals(path)

        assert frame.rows() == [(1.0, 0.1, 0.2, 0.3)]

    def test_last_comment_is_header(self, tmp_path: Path) -> None:
        """Tests that the last non-empty comment line names the columns."""
        text = "# Residuals\n# Time\tUx\n#\n1\t0.5\n"
        path = _write(tmp_path, text)

        frame = read_residuals(path)

        assert frame.columns == ["Time", "Ux"]
        assert frame.rows() == [(1.0, 0.5)]

    def test_header_only_gives_empty_frame(self, tmp_path: Path) -> None:
        """Tests that a file without data rows keeps the header columns."""
        path = _write(tmp_path, HEADER)

        frame = read_residuals(path)

        assert frame.is_empty()
        assert frame.schema == pl.Schema(
            {name: pl.Float64 for name in RESIDUAL_COLUMNS}
        )

    @pytest.mark.parametrize(
        ("text", "line"),
        [
            pytest.param("1\t0.5\n" + HEADER, 1, id="data-before-header"),
            pytest.param(HEADER + "1\t0.1\t0.2\t0.3\t0.4\n", 3, id="too-long"),
            pytest.param(HEADER + "1\t0.1\tabc\t0.3\n", 3, id="not-a-number"),
            pytest.param("", None, id="empty-file"),
            pytest.param("# \n#\n", None, id="no-header"),
        ],
    )
    def test_malformed_file_raises(
        self, tmp_path: Path, text: str, line: int | None
    ) -> None:
        """Tests that a malformed file raises with the offending line."""
        path = _write(tmp_path, text)

        with pytest.raises(FoamParseError) as error:
            read_residuals(path)

        assert error.value.path == path
        assert error.value.line == line

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Tests that a path to nothing raises `FileNotFoundError`."""
        with pytest.raises(FileNotFoundError):
            read_residuals(tmp_path / "residuals.dat")
