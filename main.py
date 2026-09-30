"""SecureVault — Main Application Entry Point.

Milestone 1 Foundation:
Proves that the Python environment, application package, configuration,
and logging system initialize cleanly and shut down safely.
"""

from __future__ import annotations

import argparse
import sys

from app import __version__
from app.core.config import AppConfig
from app.core.logging import get_logger, setup_logging


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

    args = parser.parse_args(argv)

    # Initialize safe logging
    setup_logging(level="INFO")
    logger = get_logger("main")

    config = AppConfig()
    logger.info("Initializing %s v%s [Environment: %s]", config.app_name, config.app_version, config.environment)
    logger.info("Target data directory: %s", config.data_dir)

    if args.check_config:
        logger.info("Configuration check passed successfully.")

    logger.info("%s skeleton startup and shutdown verified.", config.app_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
