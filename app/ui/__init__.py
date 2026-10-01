"""SecureVault Presentation Layer (PySide6).

Architectural Boundary:
This package encapsulates all desktop graphical interface components:
  - First-Run Setup Wizard (SetupWizard)
  - Locked View placeholder (LockedView) [M3 will implement LoginView]
  - Main Vault Dashboard (MainWindow) [M6]
  - Preferences Dialog (SettingsDialog) [M8]
"""

from app.ui.locked_view import LockedView
from app.ui.settings_dialog import SettingsDialog
from app.ui.setup.wizard import SetupWizard
from app.ui.theme import ThemeManager
from app.ui.unlocked_view import UnlockedView

__all__ = ["SetupWizard", "LockedView", "UnlockedView", "SettingsDialog", "ThemeManager"]

