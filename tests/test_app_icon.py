"""SecureVault — Application Icon Verification Tests.

Verifies the integration of the official application icon (assets/SecureVault.ico):
  - Icon file existence and validity.
  - Path resolution from source and configuration.
  - Successful loading into PySide6 QIcon with valid multi-resolution image data.
  - Central configuration on QApplication.windowIcon().
  - Automatic icon inheritance by top-level windows and dialogs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig, get_app_icon_path, get_asset_path
from app.models.credential import Credential
from app.services.initialization import InitializationService
from app.services.vault_service import VaultService
from app.ui.app_window import setup_application_icon
from app.ui.locked_view import LockedView
from app.ui.settings_dialog import SettingsDialog
from app.ui.setup.wizard import SetupWizard
from app.ui.unlocked_view import EditCredentialDialog, UnlockedView, ViewCredentialDialog


@pytest.fixture(scope="module", autouse=True)
def qapp():
    """Ensure a QApplication instance is active for icon and widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    # Configure the global application icon
    setup_application_icon(app)
    return app


class TestAppIconFile:
    """Verifies file existence, path resolution, and format of assets/SecureVault.ico."""

    def test_icon_file_exists(self) -> None:
        """Verify that the official icon file exists in the assets directory."""
        icon_path = get_app_icon_path()
        assert isinstance(icon_path, Path)
        assert icon_path.name == "SecureVault.ico"
        assert icon_path.is_file(), f"Expected icon file at '{icon_path}'"
        assert icon_path.stat().st_size > 0, "Icon file must not be empty"

    def test_asset_path_resolution(self) -> None:
        """Verify get_asset_path correctly resolves relative to project root."""
        asset_path = get_asset_path("SecureVault.ico")
        assert asset_path.exists()
        assert asset_path == get_app_icon_path()

    def test_app_config_icon_path_property(self) -> None:
        """Verify AppConfig exposes the icon path correctly."""
        config = AppConfig()
        assert config.icon_path == get_app_icon_path()
        assert config.icon_path.exists()


class TestQApplicationIcon:
    """Verifies that PySide6 loads the icon and configures QApplication centrally."""

    def test_qicon_loads_with_valid_image_data(self) -> None:
        """Verify that QIcon loads from the ICO file and contains valid image sizes."""
        icon_path = get_app_icon_path()
        icon = QIcon(str(icon_path))
        assert not icon.isNull(), "QIcon must not be null when loaded from assets/SecureVault.ico"

        sizes = icon.availableSizes()
        assert len(sizes) > 0, "Icon must provide at least one image resolution"
        # Verify valid non-zero dimensions
        assert any(size.width() >= 16 and size.height() >= 16 for size in sizes)

    def test_qapplication_has_global_window_icon(self, qapp) -> None:
        """Verify that QApplication.windowIcon() is configured and not null."""
        # Re-run setup_application_icon to verify idempotence
        configured_icon = setup_application_icon(qapp)
        assert configured_icon is not None
        assert not configured_icon.isNull()

        app_icon = QApplication.windowIcon()
        assert not app_icon.isNull(), "QApplication.windowIcon() must not be null"
        assert len(app_icon.availableSizes()) > 0


class TestWindowIconInheritance:
    """Verifies that all primary windows, wizards, and dialogs inherit the application icon."""

    def test_setup_wizard_inherits_icon(self, qapp, tmp_path: Path) -> None:
        """Verify First-Run Setup Wizard inherits the application window icon."""
        config = AppConfig(data_dir=tmp_path)
        init_service = InitializationService(config)
        vault_service = VaultService(config)
        wizard = SetupWizard(init_service=init_service, vault_service=vault_service)
        assert not wizard.windowIcon().isNull(), "SetupWizard must inherit application icon"

    def test_locked_view_inherits_icon(self, qapp) -> None:
        """Verify LockedView inherits the application window icon."""
        locked_view = LockedView()
        assert not locked_view.windowIcon().isNull(), "LockedView must inherit application icon"

    def test_unlocked_view_inherits_icon(self, qapp, tmp_path: Path) -> None:
        """Verify UnlockedView inherits the application window icon."""
        config = AppConfig(data_dir=tmp_path)
        vault_service = VaultService(config)
        from app.crypto.kdf import KDFParameters
        vault = vault_service.create_vault(
            master_password="ValidMasterPassword123!",
            kdf_params=KDFParameters.fast_for_testing(),
        )
        unlocked_view = UnlockedView(vault=vault, login_id="alice", vault_service=vault_service)
        assert not unlocked_view.windowIcon().isNull(), "UnlockedView must inherit application icon"

    def test_settings_dialog_inherits_icon(self, qapp) -> None:
        """Verify SettingsDialog inherits the application window icon."""
        settings_dlg = SettingsDialog()
        assert not settings_dlg.windowIcon().isNull(), "SettingsDialog must inherit application icon"

    def test_credential_dialogs_inherit_icon(self, qapp) -> None:
        """Verify ViewCredentialDialog and EditCredentialDialog inherit the icon."""
        cred = Credential(title="Test", username="user", password="pwd")
        view_dlg = ViewCredentialDialog(cred)
        assert not view_dlg.windowIcon().isNull(), "ViewCredentialDialog must inherit application icon"

        edit_dlg = EditCredentialDialog(cred)
        assert not edit_dlg.windowIcon().isNull(), "EditCredentialDialog must inherit application icon"
