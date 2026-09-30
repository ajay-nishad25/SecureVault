"""Automated tests for consistent application window sizing (1100 x 780).

Verifies:
  1. Centralized WINDOW_WIDTH and WINDOW_HEIGHT constants (1100 x 780).
  2. Setup Wizard initial dimensions = 1100 x 780.
  3. Login / Locked View initial dimensions = 1100 x 780.
  4. Main Vault / Unlocked View initial dimensions = 1100 x 780.
  5. ApplicationController transitions preserve 1100 x 780 across all screens.
  6. Centering helper positions windows properly on the primary screen.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.core.config import AppConfig, WINDOW_HEIGHT, WINDOW_WIDTH
from app.crypto.kdf import KDFParameters
from app.services.authentication import AuthenticationService
from app.services.initialization import InitializationService
from app.services.vault_service import VaultService
from app.ui.app_window import ApplicationController, center_window
from app.ui.locked_view import LockedView
from app.ui.setup.wizard import SetupWizard
from app.ui.unlocked_view import UnlockedView


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def test_setup(tmp_path: Path):
    """Provide initialized services and test config."""
    config = AppConfig(data_dir=tmp_path)
    init_service = InitializationService(config)
    auth_service = AuthenticationService()
    vault_service = VaultService(config)
    return config, init_service, auth_service, vault_service


def test_window_dimension_constants() -> None:
    """Verify centralized constants and AppConfig defaults are 1100x780."""
    assert WINDOW_WIDTH == 1100
    assert WINDOW_HEIGHT == 780

    config = AppConfig()
    assert config.window_width == 1100
    assert config.window_height == 780


def test_setup_wizard_initial_dimensions(qapp: QApplication, test_setup) -> None:
    """Verify Setup Wizard starts with 1100 x 780 dimensions."""
    config, init_service, _, vault_service = test_setup
    wizard = SetupWizard(init_service=init_service, vault_service=vault_service)

    assert wizard.width() == 1100
    assert wizard.height() == 780


def test_locked_view_initial_dimensions(qapp: QApplication, test_setup) -> None:
    """Verify LockedView (Login) starts with 1100 x 780 dimensions."""
    config, init_service, auth_service, vault_service = test_setup
    locked_view = LockedView(
        init_service=init_service,
        auth_service=auth_service,
        vault_service=vault_service,
    )

    assert locked_view.width() == 1100
    assert locked_view.height() == 780


def test_unlocked_view_initial_dimensions(qapp: QApplication, test_setup) -> None:
    """Verify UnlockedView (Main Vault) starts with 1100 x 780 dimensions."""
    config, _, _, vault_service = test_setup
    vault = vault_service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    unlocked_view = UnlockedView(
        vault=vault,
        login_id="alice",
        vault_service=vault_service,
    )

    assert unlocked_view.width() == 1100
    assert unlocked_view.height() == 780


def test_screen_transitions_maintain_consistent_size(qapp: QApplication, test_setup) -> None:
    """Verify ApplicationController transitions maintain 1100x780 across screens."""
    config, init_service, auth_service, vault_service = test_setup

    # Initialize vault
    vault = vault_service.create_vault(
        master_password="MasterTestPassword123!",
        kdf_params=KDFParameters.fast_for_testing(),
    )
    init_service.initialize("alice")

    controller = ApplicationController(
        config=config,
        init_service=init_service,
        auth_service=auth_service,
        vault_service=vault_service,
    )

    # 1. Start on LockedView
    controller.start()
    assert controller.current_window is not None
    assert controller.current_window.width() == 1100
    assert controller.current_window.height() == 780
    assert isinstance(controller.current_window, LockedView)

    # 2. Transition to UnlockedView
    controller._on_vault_unlocked(vault)
    assert controller.current_window is not None
    assert controller.current_window.width() == 1100
    assert controller.current_window.height() == 780
    assert isinstance(controller.current_window, UnlockedView)

    # 3. Transition back to LockedView
    controller._on_vault_locked()
    assert controller.current_window is not None
    assert controller.current_window.width() == 1100
    assert controller.current_window.height() == 780
    assert isinstance(controller.current_window, LockedView)


def test_center_window_utility(qapp: QApplication, test_setup) -> None:
    """Verify center_window positions a widget properly without error."""
    _, init_service, auth_service, vault_service = test_setup
    locked_view = LockedView(
        init_service=init_service,
        auth_service=auth_service,
        vault_service=vault_service,
    )

    center_window(locked_view)
    assert locked_view.width() == 1100
    assert locked_view.height() == 780
