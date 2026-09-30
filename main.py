"""SecureVault — Main Application Entry Point.

Milestone 2:
Launches the PySide6 First-Run Setup Wizard if the application is uninitialized,
or transitions to the Locked state placeholder if already initialized.
"""

from __future__ import annotations

import argparse
import sys

from app import __version__
from app.core.config import AppConfig
from app.core.logging import get_logger, setup_logging
from app.services.initialization import InitializationService
from app.ui.app_window import run_gui


def main(argv: list[str] | None = None) -> int:
    """Execute the application startup and shutdown lifecycle.

    Returns:
        int: Process exit code (0 for successful run).
    """
    parser = argparse.ArgumentParser(
        prog="SecureVault",
        description="Completely offline, local-first desktop password manager.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Verify application configuration and data directory resolution.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run startup checks headlessly without opening the GUI window.",
    )

    args = parser.parse_args(argv)

    # Initialize safe logging
    setup_logging(level="INFO")
    logger = get_logger("main")

    config = AppConfig()
    logger.info("Initializing %s v%s [Environment: %s]", config.app_name, config.app_version, config.environment)
    logger.info("Target data directory: %s", config.data_dir)

    init_service = InitializationService(config)
    session_state = init_service.get_session_state()
    logger.info("Current session state: %s", session_state)

    if args.check_config or args.headless:
        logger.info("Headless check passed successfully.")
        return 0

    # Launch desktop PySide6 interface
    return run_gui(config)


if __name__ == "__main__":
    sys.exit(main())
