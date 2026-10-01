"""SecureVault — Centralized Theme Management (Milestone M8.2).

Provides application-wide Dark and Light theme stylesheets and runtime theme
switching via ThemeManager.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

DARK_THEME = "dark"
LIGHT_THEME = "light"
SUPPORTED_THEMES = (DARK_THEME, LIGHT_THEME)

# -----------------------------------------------------------------------------
# Dark Theme Stylesheet (GitHub Dark-inspired palette)
# -----------------------------------------------------------------------------
DARK_THEME_QSS = """
/* Global Window and Base Styles */
QWidget {
    background-color: #0d1117;
    color: #f0f6fc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QDialog, QMessageBox, QWizard {
    background-color: #161b22;
    color: #f0f6fc;
    border: 1px solid #30363d;
}

/* Headers and Labels */
QLabel {
    background-color: transparent;
    color: #f0f6fc;
}

QLabel#AutoLockCountdown {
    color: #e3b341;
    font-size: 12px;
    font-family: monospace;
    font-weight: 600;
}

QLabel#VaultHeaderUnlocked {
    font-size: 20px;
    font-weight: bold;
    color: #44bb44;
}

QLabel#VaultMetaLabel {
    color: #adbac7;
}

QLabel#CounterLabel {
    font-weight: bold;
    font-size: 13px;
    margin-top: 4px;
    color: #c9d1d9;
}

QLabel#SettingsTitleLabel, QLabel#GeneralHeader, QLabel#SecurityHeader {
    color: #f0f6fc;
    font-size: 18px;
    font-weight: bold;
}

QLabel#AppearanceTitle, QLabel#AutoLockTitle, QLabel#MasterPasswordTitle {
    color: #58a6ff;
    font-size: 14px;
    font-weight: bold;
}

QLabel#AppearanceDescription, QLabel#AutoLockDescription, QLabel#MasterPasswordDescription {
    color: #8b949e;
    font-size: 12px;
}

QLabel#CurrentThemeStatus, QLabel#CurrentTimeoutStatus {
    color: #6e7681;
    font-size: 11px;
}

QLabel#PasswordNoteLabel {
    color: #8b949e;
    font-size: 11px;
    font-style: italic;
}

QLabel#EmptyStateIcon {
    font-size: 28px;
    color: #8b949e;
    background: transparent;
    border: none;
}

QLabel#EmptyStateTitle {
    font-size: 15px;
    font-weight: bold;
    color: #8b949e;
    background: transparent;
    border: none;
}

QLabel#EmptyStateSubtitle {
    font-size: 13px;
    color: #6e7681;
    background: transparent;
    border: none;
}

/* Credential Card Labels */
QLabel#CardTitle {
    font-size: 14px;
    font-weight: bold;
    color: #f0f6fc;
}

QLabel#CardUsername {
    font-size: 12px;
    color: #8b949e;
}

QLabel#CardNotes {
    font-size: 11px;
    color: #768390;
    font-style: italic;
}

/* Input Fields */
QLineEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f6fc;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #58a6ff;
}

QLineEdit:read-only, QLineEdit[readOnly="true"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    color: #c9d1d9;
}

QLineEdit#SearchInput {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #c9d1d9;
    font-size: 13px;
}

QLineEdit#SearchInput:focus {
    border-color: #58a6ff;
}

/* Push Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    color: #f0f6fc;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* Primary Action Buttons */
QPushButton:default, QPushButton#PrimaryButton, QPushButton#ChangePasswordButton {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    font-weight: 600;
}

QPushButton:default:hover, QPushButton#PrimaryButton:hover, QPushButton#ChangePasswordButton:hover {
    background-color: #2ea043;
    border-color: #3fb950;
}

/* Danger / Delete Buttons */
QPushButton#DeleteButton {
    background-color: #21262d;
    color: #f85149;
    border: 1px solid #da3633;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#DeleteButton:hover {
    background-color: #da3633;
    color: #ffffff;
    border-color: #f85149;
}

/* Settings Close Button */
QPushButton#SettingsCloseButton {
    background-color: transparent;
    color: #8b949e;
    font-size: 15px;
    font-weight: bold;
    border: 1px solid transparent;
    border-radius: 6px;
}

QPushButton#SettingsCloseButton:hover {
    background-color: #21262d;
    color: #f0f6fc;
    border: 1px solid #30363d;
}

/* Clear Search Button */
QPushButton#ClearSearchButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}

QPushButton#ClearSearchButton:hover {
    background-color: #30363d;
}

/* Card Action Buttons */
QPushButton#CardViewBtn {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CardViewBtn:hover {
    background-color: #30363d;
    color: #f0f6fc;
}

QPushButton#CardEditBtn {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #388bfd;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CardEditBtn:hover {
    background-color: #388bfd;
}

/* Copy Credential Buttons */
QPushButton#CopyUsernameBtn, QPushButton#CopyPasswordBtn {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CopyUsernameBtn:hover, QPushButton#CopyPasswordBtn:hover {
    background-color: #30363d;
    color: #f0f6fc;
    border-color: #8b949e;
}

QLabel#ViewDialogStatus {
    font-size: 11px;
    font-weight: bold;
    color: #3fb950;
    background: transparent;
    border: none;
}

/* Radio Buttons and Checkboxes */
QRadioButton, QCheckBox {
    background-color: transparent;
    color: #f0f6fc;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #30363d;
    background-color: #0d1117;
}

QRadioButton::indicator:checked {
    border: 4px solid #58a6ff;
    background-color: #0d1117;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background-color: #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #58a6ff;
}

/* List Widgets */
QListWidget {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    border-radius: 6px;
    padding: 4px;
}

QListWidget#CredentialList {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px;
    outline: none;
}

QListWidget#CredentialList::item {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}

QListWidget#CredentialList::item:selected, QListWidget#CredentialList::item:hover {
    background: transparent;
}

/* Settings Sidebar */
QListWidget#SettingsSidebar {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px;
}

QListWidget#SettingsSidebar::item {
    color: #8b949e;
    padding: 10px 14px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
}

QListWidget#SettingsSidebar::item:selected {
    background-color: #21262d;
    color: #f0f6fc;
}

QListWidget#SettingsSidebar::item:hover:!selected {
    background-color: #161b22;
    color: #c9d1d9;
}

/* Section Cards in Settings */
QFrame#AppearanceSection, QFrame#AutoLockSection, QFrame#MasterPasswordSection {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
}

/* Dividers */
QFrame#SettingsDivider {
    background-color: #30363d;
    max-height: 1px;
    border: none;
}

/* Credential Card Widget */
CredentialCardWidget {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}

CredentialCardWidget:hover {
    border: 1px solid #444c56;
}

/* Empty State Box */
QWidget#EmptyStateWidget {
    background-color: #161b22;
    border: 1px dashed #30363d;
    border-radius: 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #0d1117;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    background-color: #0d1117;
    color: #f0f6fc;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 3px;
}
"""

# -----------------------------------------------------------------------------
# Light Theme Stylesheet (GitHub Light-inspired palette)
# -----------------------------------------------------------------------------
LIGHT_THEME_QSS = """
/* Global Window and Base Styles */
QWidget {
    background-color: #f6f8fa;
    color: #1f2328;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QDialog, QMessageBox, QWizard {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
}

/* Headers and Labels */
QLabel {
    background-color: transparent;
    color: #1f2328;
}

QLabel#AutoLockCountdown {
    color: #9a6700;
    font-size: 12px;
    font-family: monospace;
    font-weight: 600;
}

QLabel#VaultHeaderUnlocked {
    font-size: 20px;
    font-weight: bold;
    color: #1a7f37;
}

QLabel#VaultMetaLabel {
    color: #57606a;
}

QLabel#CounterLabel {
    font-weight: bold;
    font-size: 13px;
    margin-top: 4px;
    color: #1f2328;
}

QLabel#SettingsTitleLabel, QLabel#GeneralHeader, QLabel#SecurityHeader {
    color: #1f2328;
    font-size: 18px;
    font-weight: bold;
}

QLabel#AppearanceTitle, QLabel#AutoLockTitle, QLabel#MasterPasswordTitle {
    color: #0969da;
    font-size: 14px;
    font-weight: bold;
}

QLabel#AppearanceDescription, QLabel#AutoLockDescription, QLabel#MasterPasswordDescription {
    color: #57606a;
    font-size: 12px;
}

QLabel#CurrentThemeStatus, QLabel#CurrentTimeoutStatus {
    color: #57606a;
    font-size: 11px;
}

QLabel#PasswordNoteLabel {
    color: #57606a;
    font-size: 11px;
    font-style: italic;
}

QLabel#EmptyStateIcon {
    font-size: 28px;
    color: #57606a;
    background: transparent;
    border: none;
}

QLabel#EmptyStateTitle {
    font-size: 15px;
    font-weight: bold;
    color: #57606a;
    background: transparent;
    border: none;
}

QLabel#EmptyStateSubtitle {
    font-size: 13px;
    color: #6e7781;
    background: transparent;
    border: none;
}

/* Credential Card Labels */
QLabel#CardTitle {
    font-size: 14px;
    font-weight: bold;
    color: #1f2328;
}

QLabel#CardUsername {
    font-size: 12px;
    color: #57606a;
}

QLabel#CardNotes {
    font-size: 11px;
    color: #6e7781;
    font-style: italic;
}

/* Input Fields */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1f2328;
    selection-background-color: #0969da;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #0969da;
}

QLineEdit:read-only, QLineEdit[readOnly="true"] {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    color: #57606a;
}

QLineEdit#SearchInput {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1f2328;
    font-size: 13px;
}

QLineEdit#SearchInput:focus {
    border-color: #0969da;
}

/* Push Buttons */
QPushButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #eaeef2;
    color: #1f2328;
    border-color: #afb8c1;
}

QPushButton:pressed {
    background-color: #e1e4e8;
}

QPushButton:disabled {
    background-color: #f6f8fa;
    color: #8c959f;
    border-color: #d0d7de;
}

/* Primary Action Buttons */
QPushButton:default, QPushButton#PrimaryButton, QPushButton#ChangePasswordButton {
    background-color: #1f883d;
    color: #ffffff;
    border: 1px solid #1a7f37;
    font-weight: 600;
}

QPushButton:default:hover, QPushButton#PrimaryButton:hover, QPushButton#ChangePasswordButton:hover {
    background-color: #1a7f37;
    border-color: #116329;
}

/* Danger / Delete Buttons */
QPushButton#DeleteButton {
    background-color: #f6f8fa;
    color: #cf222e;
    border: 1px solid #cf222e;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#DeleteButton:hover {
    background-color: #cf222e;
    color: #ffffff;
    border-color: #cf222e;
}

/* Settings Close Button */
QPushButton#SettingsCloseButton {
    background-color: transparent;
    color: #57606a;
    font-size: 15px;
    font-weight: bold;
    border: 1px solid transparent;
    border-radius: 6px;
}

QPushButton#SettingsCloseButton:hover {
    background-color: #eaeef2;
    color: #1f2328;
    border: 1px solid #d0d7de;
}

/* Clear Search Button */
QPushButton#ClearSearchButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}

QPushButton#ClearSearchButton:hover {
    background-color: #eaeef2;
}

/* Card Action Buttons */
QPushButton#CardViewBtn {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CardViewBtn:hover {
    background-color: #eaeef2;
    color: #1f2328;
}

QPushButton#CardEditBtn {
    background-color: #0969da;
    color: #ffffff;
    border: 1px solid #0969da;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CardEditBtn:hover {
    background-color: #0860ca;
}

/* Copy Credential Buttons */
QPushButton#CopyUsernameBtn, QPushButton#CopyPasswordBtn {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#CopyUsernameBtn:hover, QPushButton#CopyPasswordBtn:hover {
    background-color: #eaeef2;
    color: #0969da;
    border-color: #afb8c1;
}

QLabel#ViewDialogStatus {
    font-size: 11px;
    font-weight: bold;
    color: #1a7f37;
    background: transparent;
    border: none;
}

/* Radio Buttons and Checkboxes */
QRadioButton, QCheckBox {
    background-color: transparent;
    color: #1f2328;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #d0d7de;
    background-color: #ffffff;
}

QRadioButton::indicator:checked {
    border: 4px solid #0969da;
    background-color: #ffffff;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #d0d7de;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #0969da;
    border-color: #0969da;
}

/* List Widgets */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    border-radius: 6px;
    padding: 4px;
}

QListWidget#CredentialList {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px;
    outline: none;
}

QListWidget#CredentialList::item {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}

QListWidget#CredentialList::item:selected, QListWidget#CredentialList::item:hover {
    background: transparent;
}

/* Settings Sidebar */
QListWidget#SettingsSidebar {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 6px;
}

QListWidget#SettingsSidebar::item {
    color: #57606a;
    padding: 10px 14px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
}

QListWidget#SettingsSidebar::item:selected {
    background-color: #eaeef2;
    color: #1f2328;
}

QListWidget#SettingsSidebar::item:hover:!selected {
    background-color: #f3f4f6;
    color: #24292f;
}

/* Section Cards in Settings */
QFrame#AppearanceSection, QFrame#AutoLockSection, QFrame#MasterPasswordSection {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px;
}

/* Dividers */
QFrame#SettingsDivider {
    background-color: #d0d7de;
    max-height: 1px;
    border: none;
}

/* Credential Card Widget */
CredentialCardWidget {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
}

CredentialCardWidget:hover {
    border: 1px solid #0969da;
}

/* Empty State Box */
QWidget#EmptyStateWidget {
    background-color: #ffffff;
    border: 1px dashed #d0d7de;
    border-radius: 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #f6f8fa;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #d0d7de;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #afb8c1;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #d0d7de;
    border-radius: 4px;
    text-align: center;
    background-color: #ffffff;
    color: #1f2328;
}

QProgressBar::chunk {
    background-color: #1f883d;
    border-radius: 3px;
}
"""


class ThemeManager(QObject):
    """Centralized manager for Dark and Light themes across all SecureVault UI."""

    theme_changed = Signal(str)

    _instance: ThemeManager | None = None

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_theme: str = DARK_THEME

    @classmethod
    def instance(cls) -> ThemeManager:
        """Return the singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def current_theme(self) -> str:
        """Return the name of the currently active theme."""
        return self._current_theme

    def get_theme(self) -> str:
        """Retrieve current theme name."""
        return self._current_theme

    def get_stylesheet(self, theme_name: str | None = None) -> str:
        """Return the QSS stylesheet for the specified or current theme."""
        theme = theme_name or self._current_theme
        if theme == LIGHT_THEME:
            return LIGHT_THEME_QSS
        return DARK_THEME_QSS

    def apply_dark_theme(self, app: QApplication | None = None) -> None:
        """Convenience method to apply Dark theme."""
        self.apply_theme(DARK_THEME, app)

    def apply_light_theme(self, app: QApplication | None = None) -> None:
        """Convenience method to apply Light theme."""
        self.apply_theme(LIGHT_THEME, app)

    def apply_theme(self, theme_name: str, app: QApplication | None = None) -> None:
        """Apply the specified theme to the application at runtime.

        Args:
            theme_name: 'dark' or 'light'
            app: Optional QApplication instance (defaults to QApplication.instance())

        Raises:
            ValueError: If theme_name is not supported.
        """
        if theme_name not in SUPPORTED_THEMES:
            raise ValueError(
                f"Unsupported theme '{theme_name}'. Supported themes: {SUPPORTED_THEMES}"
            )

        self._current_theme = theme_name
        target_app = app or QApplication.instance()
        if target_app is not None:
            stylesheet = self.get_stylesheet(theme_name)
            target_app.setStyleSheet(stylesheet)

        self.theme_changed.emit(theme_name)

    def switch_theme(self, theme_name: str, app: QApplication | None = None) -> None:
        """Alias for apply_theme."""
        self.apply_theme(theme_name, app)


def get_current_theme() -> str:
    """Convenience function returning the active theme name."""
    return ThemeManager.instance().get_theme()


def apply_theme(theme_name: str, app: QApplication | None = None) -> None:
    """Convenience function applying theme by name."""
    ThemeManager.instance().apply_theme(theme_name, app)
