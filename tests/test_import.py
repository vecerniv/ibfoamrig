"""Basic import tests for the ibfoamrig package and its public API."""

import importlib
import importlib.metadata
import importlib.util
import subprocess
import sys

import pytest

import ibfoamrig

PUBLIC_MODULES = [
    "ibfoamrig",
    "ibfoamrig.core",
    "ibfoamrig.io",
    "ibfoamrig.plot",
    "ibfoamrig.typing",
]


def test_package_is_discoverable() -> None:
    """Tests that ibfoamrig can be located as a package without importing it."""
    spec = importlib.util.find_spec("ibfoamrig")

    assert spec is not None
    assert spec.submodule_search_locations is not None


@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_public_names_exist(module_name: str) -> None:
    """Tests that every name in ``__all__`` is defined in its module."""
    module = importlib.import_module(module_name)

    missing = [name for name in module.__all__ if not hasattr(module, name)]

    assert not missing


@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_public_names_are_unique(module_name: str) -> None:
    """Tests that ``__all__`` lists each name only once."""
    module = importlib.import_module(module_name)

    assert len(module.__all__) == len(set(module.__all__))


def test_version_matches_metadata() -> None:
    """Tests that ``__version__`` is the installed distribution version."""
    assert ibfoamrig.__version__ == importlib.metadata.version("ibfoamrig")


def test_import_does_not_load_matplotlib() -> None:
    """Tests that importing the top-level package leaves matplotlib unloaded.

    Runs in a fresh interpreter, since other tests may already have imported
    `ibfoamrig.plot` into this one.
    """
    code = "import sys, ibfoamrig; sys.exit('matplotlib' in sys.modules)"

    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0
