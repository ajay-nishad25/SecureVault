"""SecureVault — First-Run Setup Wizard.

Implements the multi-step onboarding wizard using PySide6 QWizard.
Guides the user through security terms, no-recovery acknowledgment,
Login ID selection, and master password input.

CRITICAL SECURITY CONSTRAINT:
Passwords entered in this wizard are transient in-memory values.
They are NEVER logged, printed, or written to disk.
On completion, only non-sensitive initialization metadata is persisted.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from app.core.logging import get_logger
from app.core.validation import (
    estimate_password_strength,
    validate_login_id,
    validate_master_password,
)
from app.services.initialization import InitializationService
from app.services.vault_service import VaultService

logger = get_logger("ui.setup.wizard")


class WelcomePage(QWizardPage):
    """First page introducing SecureVault and its local-first philosophy."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to SecureVault")
        self.setSubTitle("Completely offline, local-first personal password manager.")

        layout = QVBoxLayout()
        layout.setSpacing(16)

        intro = QLabel(
            "SecureVault is designed to keep your credentials strictly in your personal custody.\n\n"
            "Key Foundations:\n"
            "  • 100% Offline: No cloud servers, no account synchronization, zero telemetry.\n"
            "  • Local Custody: Your credentials are encrypted and stored on your local machine.\n"
            "  • Open & Auditable: Built with standard, peer-reviewed cryptographic primitives.\n\n"
            "Click 'Next' to review the security principles and configure your vault."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addStretch()

        self.setLayout(layout)


class FeaturesPage(QWizardPage):
    """Second page explaining core security architecture principles."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Security Architecture Principles")
        self.setSubTitle("Understand how SecureVault protects your data.")

        layout = QVBoxLayout()
        layout.setSpacing(14)

        content = QLabel(
            "Before continuing, please familiarize yourself with the design principles of Version 1:\n\n"
            "1. Local Storage Only\n"
            "   Your vault resides as a local encrypted file on your device. There is no remote backup.\n\n"
            "2. Mathematical Security\n"
            "   Vault contents are protected using Argon2id password key derivation and AES-256-GCM authenticated encryption.\n\n"
            "3. Zero Backdoors\n"
            "   Only the possessor of the master password can decrypt the vault. No emergency keys or escrow systems exist.\n\n"
            "4. Absolute Custody\n"
            "   You bear full responsibility for protecting and remembering your master password."
        )
        content.setWordWrap(True)
        layout.addWidget(content)
        layout.addStretch()

        self.setLayout(layout)


class AcknowledgementPage(QWizardPage):
    """Third page enforcing explicit agreement with the no-recovery security policy."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("No-Recovery Security Notice")
        self.setSubTitle("Mandatory acknowledgement of the Zero-Knowledge security model.")

        layout = QVBoxLayout()
        layout.setSpacing(16)

        warning_box = QLabel(
            "⚠️ CRITICAL SECURITY WARNING:\n\n"
            "SecureVault Version 1 does NOT contain any password recovery mechanism, "
            "security questions, recovery phrase, or administrative reset.\n\n"
            "If you forget your master password, your vault CANNOT be recovered by anyone.\n"
            "All stored passwords, notes, and records will be permanently inaccessible."
        )
        warning_box.setWordWrap(True)
        warning_box.setStyleSheet(
            "background-color: #2b1f1f; color: #ff9999; padding: 14px; border: 1px solid #772222; border-radius: 6px;"
        )
        layout.addWidget(warning_box)

        self.ack_checkbox = QCheckBox(
            "I understand that SecureVault v1 has no password recovery mechanism."
        )
        self.ack_checkbox.toggled.connect(self.completeChanged)
        layout.addWidget(self.ack_checkbox)
        layout.addStretch()

        self.setLayout(layout)

    def isComplete(self) -> bool:
        return self.ack_checkbox.isChecked()


class LoginIdPage(QWizardPage):
    """Fourth page for configuring the non-sensitive Login ID."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Create Login Identifier")
        self.setSubTitle("Choose a non-secret user identifier for this workstation.")

        layout = QVBoxLayout()
        layout.setSpacing(12)

        desc = QLabel(
            "Enter a username or identifier. This is a non-sensitive label used to identify your local profile."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form_layout = QFormLayout()
        self.login_id_input = QLineEdit()
        self.login_id_input.setPlaceholderText("e.g. alice, developer, or user@example.com")
        self.login_id_input.textChanged.connect(self._on_text_changed)
        form_layout.addRow("Login ID:", self.login_id_input)
        layout.addLayout(form_layout)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)
        layout.addStretch()

        self.setLayout(layout)

    def _on_text_changed(self) -> None:
        text = self.login_id_input.text().strip()
        is_valid, error = validate_login_id(text)
        if not text:
            self.validation_label.setText("")
        elif is_valid:
            self.validation_label.setText("✓ Valid Login ID")
            self.validation_label.setStyleSheet("color: #44bb44;")
        else:
            self.validation_label.setText(f"✕ {error}")
            self.validation_label.setStyleSheet("color: #ee5555;")

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        text = self.login_id_input.text().strip()
        is_valid, _ = validate_login_id(text)
        return is_valid

    def get_login_id(self) -> str:
        return self.login_id_input.text().strip()


class MasterPasswordPage(QWizardPage):
    """Fifth page for setting and confirming the master password."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Create Master Password")
        self.setSubTitle("This master password will protect your encrypted vault.")

        layout = QVBoxLayout()
        layout.setSpacing(12)

        info = QLabel(
            "Choose a strong master password. We recommend at least 12 characters combining uppercase, "
            "lowercase, numbers, and symbols, or a memorable multi-word passphrase."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form_layout = QFormLayout()

        # Password input + toggle
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter master password (min 8 chars)")
        self.password_input.textChanged.connect(self._on_password_changed)

        self.show_password_cb = QCheckBox("Show password")
        self.show_password_cb.toggled.connect(self._toggle_visibility)

        pw_layout = QVBoxLayout()
        pw_layout.addWidget(self.password_input)
        pw_layout.addWidget(self.show_password_cb)
        form_layout.addRow("Master Password:", pw_layout)

        # Confirm password input
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Re-enter master password")
        self.confirm_input.textChanged.connect(self._on_password_changed)
        form_layout.addRow("Confirm Password:", self.confirm_input)

        layout.addLayout(form_layout)

        # Strength meter
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Strength (Advisory):"))
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        strength_layout.addWidget(self.strength_bar)
        self.strength_label = QLabel("None")
        strength_layout.addWidget(self.strength_label)
        layout.addLayout(strength_layout)

        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        layout.addWidget(self.feedback_label)
        layout.addStretch()

        self.setLayout(layout)

    def _toggle_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)

    def _on_password_changed(self) -> None:
        pwd = self.password_input.text()
        confirm = self.confirm_input.text()

        # Update advisory strength meter
        rating, score = estimate_password_strength(pwd)
        self.strength_bar.setValue(score)
        self.strength_label.setText(rating)

        # Validation feedback
        is_valid, error = validate_master_password(pwd, confirm)
        if not pwd:
            self.feedback_label.setText("")
        elif is_valid:
            self.feedback_label.setText("✓ Passwords match and meet requirements.")
            self.feedback_label.setStyleSheet("color: #44bb44;")
        else:
            self.feedback_label.setText(f"✕ {error}")
            self.feedback_label.setStyleSheet("color: #ee5555;")

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        pwd = self.password_input.text()
        confirm = self.confirm_input.text()
        is_valid, _ = validate_master_password(pwd, confirm)
        return is_valid

    def get_password(self) -> str:
        """Return the master password text."""
        return self.password_input.text()

    def clear_sensitive_inputs(self) -> None:
        """Clear password text from line edit controls to minimize memory residence."""
        self.password_input.clear()
        self.confirm_input.clear()



class FinalWarningPage(QWizardPage):
    """Sixth page confirming all configured parameters before completing initialization."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Final Confirmation")
        self.setSubTitle("Review your settings before completing initial setup.")

        layout = QVBoxLayout()
        layout.setSpacing(14)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        warning = QLabel(
            "By checking below, you confirm that you have recorded your master password securely. "
            "SecureVault cannot assist you in recovering access if this password is forgotten."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        self.confirm_checkbox = QCheckBox(
            "I understand and want to initialize SecureVault."
        )
        self.confirm_checkbox.toggled.connect(self.completeChanged)
        layout.addWidget(self.confirm_checkbox)
        layout.addStretch()

        self.setLayout(layout)

    def initializePage(self) -> None:
        wizard = self.wizard()
        login_id = wizard.get_login_id() if hasattr(wizard, "get_login_id") else "Unknown"
        self.summary_label.setText(
            f"Configuration Summary:\n"
            f"  • Login ID: {login_id}\n"
            f"  • Master Password: [Configured]\n"
            f"  • Recovery Mechanism: None (Zero-Knowledge v1)\n"
        )

    def isComplete(self) -> bool:
        return self.confirm_checkbox.isChecked()


class CompletionPage(QWizardPage):
    """Final wizard page indicating setup is complete."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("SecureVault has been successfully configured.")

        layout = QVBoxLayout()
        layout.setSpacing(16)

        msg = QLabel(
            "✓ First-run setup is complete!\n\n"
            "Next Steps:\n"
            "The application will now enter the LOCKED state. When you launch SecureVault in the future, "
            "you will be prompted to authenticate with your master password.\n\n"
            "Note: Cryptographic vault storage and unlock verification will be activated in Milestones M3 and M4.\n\n"
            "Click 'Finish' to exit setup."
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)
        layout.addStretch()

        self.setLayout(layout)


class SetupWizard(QWizard):
    """First-run setup wizard guiding the user through initial onboarding."""

    setup_completed = Signal(str)  # Emits login_id upon successful setup

    def __init__(
        self,
        init_service: InitializationService | None = None,
        vault_service: VaultService | None = None,
    ) -> None:
        super().__init__()
        self._init_service = init_service or InitializationService()
        self._vault_service = vault_service or VaultService(self._init_service.config)
        self._setup_successful: bool = False

        self.setWindowTitle("SecureVault — First-Run Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(650, 480)

        # Instantiate pages
        self.welcome_page = WelcomePage()
        self.features_page = FeaturesPage()
        self.ack_page = AcknowledgementPage()
        self.login_id_page = LoginIdPage()
        self.password_page = MasterPasswordPage()
        self.warning_page = FinalWarningPage()
        self.completion_page = CompletionPage()

        # Add pages in exact order
        self.addPage(self.welcome_page)
        self.addPage(self.features_page)
        self.addPage(self.ack_page)
        self.addPage(self.login_id_page)
        self.addPage(self.password_page)
        self.addPage(self.warning_page)
        self.addPage(self.completion_page)

    def get_login_id(self) -> str:
        """Retrieve the configured Login ID from the login ID page."""
        return self.login_id_page.get_login_id()

    def get_password(self) -> str:
        """Retrieve the master password entered in the password page."""
        return self.password_page.get_password()

    def accept(self) -> None:
        """Handle wizard completion."""
        login_id = self.get_login_id()
        password = self.get_password()
        logger.info("Setup wizard completed. Creating encrypted vault and initializing for user '%s'.", login_id)

        try:
            # Create encrypted .svault file if master password was configured
            if password:
                self._vault_service.create_vault(password)

            # Initialize non-sensitive application state
            self._init_service.initialize(login_id)
            self._setup_successful = True
            self.setup_completed.emit(login_id)
        except Exception as err:
            logger.error("Failed to complete setup and create vault: %s", err)
            self._setup_successful = False
            raise
        finally:
            # Clear sensitive password inputs from UI memory immediately
            self.password_page.clear_sensitive_inputs()
            password = ""

        super().accept()

    def reject(self) -> None:
        """Handle setup cancellation."""
        logger.info("Setup wizard cancelled by user. No initialization state created.")
        self.password_page.clear_sensitive_inputs()
        self._setup_successful = False
        super().reject()

    def is_setup_successful(self) -> bool:
        """Check if setup wizard completed successfully."""
        return self._setup_successful
