"""Tests for package structure and version definition."""

import app
import app.core
import app.crypto
import app.models
import app.services
import app.storage
import app.ui


def test_package_version_defined() -> None:
    """Verify that __version__ is defined centrally and is valid."""
    assert hasattr(app, "__version__")
    assert isinstance(app.__version__, str)
    assert app.__version__ == "0.1.0"


def test_subpackages_importable() -> None:
    """Verify that all core architectural subsystem packages are importable."""
    assert app.core is not None
    assert app.crypto is not None
    assert app.storage is not None
    assert app.services is not None
    assert app.models is not None
    assert app.ui is not None
