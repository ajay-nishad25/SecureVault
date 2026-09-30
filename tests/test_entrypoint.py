"""Tests for the main application entry point."""

from main import main


def test_main_default_execution() -> None:
    """Verify that main() executes cleanly and exits with code 0."""
    exit_code = main(argv=[])
    assert exit_code == 0


def test_main_check_config_execution() -> None:
    """Verify that main() executes with --check-config flag and exits with code 0."""
    exit_code = main(argv=["--check-config"])
    assert exit_code == 0
