"""Basic import tests for the lutils package."""

import importlib.util


def test_package_is_discoverable() -> None:
    """Tests that lutils can be located as a package without importing it."""
    spec = importlib.util.find_spec("lutils")

    assert spec is not None
    assert spec.submodule_search_locations is not None
