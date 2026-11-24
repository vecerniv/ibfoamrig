"""Basic import tests for the ibfoamrig package."""

import importlib.util


def test_package_is_discoverable() -> None:
    """Tests that ibfoamrig can be located as a package without importing it."""
    spec = importlib.util.find_spec("ibfoamrig")

    assert spec is not None
    assert spec.submodule_search_locations is not None
