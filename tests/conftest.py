"""Shared fixtures for the ibfoamrig test suite."""

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Returns the directory holding the OpenFOAM test cases."""
    return DATA_DIR
