"""Tests for the main application entry point."""

from unittest.mock import patch
from main import main


def test_main_headless_execution() -> None:
    """Verify that main() executes with --headless flag and exits with code 0."""
    exit_code = main(argv=["--headless"])
    assert exit_code == 0


def test_main_check_config_execution() -> None:
    """Verify that main() executes with --check-config flag and exits with code 0."""
    exit_code = main(argv=["--check-config"])
    assert exit_code == 0


def test_main_default_gui_invoked() -> None:
    """Verify that running main() with default arguments invokes run_gui."""
    with patch("main.run_gui", return_value=0) as mock_run_gui:
        exit_code = main(argv=[])
        assert exit_code == 0
        mock_run_gui.assert_called_once()
