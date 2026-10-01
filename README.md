# SecureVault

**SecureVault** is an open-source, completely offline desktop password manager built with Python and PySide6. It is designed for users who demand absolute privacy, zero-cloud architecture, and robust local cryptographic security.

---

## Current Status

- **Current Milestone**: `M13 — Windows Packaging` (Complete / Verified)
- **Active Version**: `0.1.0`
- **Application State**: Fully realized production desktop application. Includes First-Run Setup Wizard, Argon2id authentication, 134-byte fixed binary envelope (`vault.svault`), AES-256-GCM DEK wrapping, encrypted credential CRUD, live search, 2-stage session auto-lock, settings and light/dark theme switching, safe clipboard watchdog with auto-clear, deterministic ephemeral memory wiping, and standalone Windows executable (`SecureVault.exe`) and Inno Setup installer (`SecureVault-Setup-0.1.0.exe`).
- **Data Isolation**: Application installation resides under `C:\Program Files\SecureVault\` (or custom dir), while all encrypted user data strictly resides under `%LOCALAPPDATA%\SecureVault\` and survives application uninstallation.

---

## Technical Stack

- **Language**: Python 3.11+ (Tested on Python 3.11.4)
- **GUI Toolkit**: PySide6 (Qt 6 for Python)
- **Cryptographic Libraries**: `argon2-cffi` (Argon2id KDF), `cryptography` (AES-256-GCM AEAD, DEK wrapping, payload encryption), standard `secrets` CSPRNG
- **Packaging Tools**: PyInstaller 6.12.0+, Inno Setup 6
- **Test Runner**: `pytest` (378 passing tests)
- **Target Platform**: Windows 10/11 (with cross-platform architecture targeting Linux in post-v1)

---

## Developer Quickstart

### 1. Prerequisites
Ensure Python 3.11 or higher is installed and available on your system path:
```bash
python --version
```

### 2. Create and Activate Virtual Environment
```powershell
# Create local virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
# Install runtime dependencies (PySide6, argon2-cffi, cryptography)
pip install -r requirements.txt

# Or install all development and testing dependencies (including pytest)
pip install -r requirements-dev.txt
```

### 4. Run the Application
```powershell
# Launch the desktop PySide6 application
# (Opens Setup Wizard on first run, or Locked View if initialized)
python main.py

# Verify configuration and data directory resolution headlessly
python main.py --check-config

# Run headless startup check without opening the GUI
python main.py --headless

# Display version
python main.py --version
```

### 5. Run the Test Suite
```powershell
# Run all 378 unit, integration, and UI tests
pytest

# Run tests with verbose output
pytest -v
```

---

## Production Packaging & Installer

SecureVault produces a standalone Windows application and standard installer.

### Build Standalone Executable (PyInstaller)
```powershell
# Build standalone directory bundle (dist/SecureVault/SecureVault.exe)
pyinstaller packaging/SecureVault.spec --noconfirm --clean
```
The resulting executable is located at `dist/SecureVault/SecureVault.exe`. It runs without Python or virtual environment installed, displays the native `SecureVault.ico` icon, and opens no console window.

### Build Windows Installer (Inno Setup)
```powershell
# Compile installer with Inno Setup Compiler (ISCC)
iscc packaging/SecureVault.iss
```
The resulting installer is generated at `dist_installer/SecureVault-Setup-0.1.0.exe`.

**User Data Safety Guarantee**: The installer installs the application to `{autopf}\SecureVault` and creates shortcuts with the custom icon. During uninstallation, user vault data in `%LOCALAPPDATA%\SecureVault` is strictly preserved and never deleted.

---

## Package Structure

```text
SecureVault/
├── app/
│   ├── __init__.py       # Central version definition (__version__ = "0.1.0")
│   ├── core/             # AppConfig, Safe Logging, Domain Exceptions, Validation
│   ├── crypto/           # Argon2id KDF & AES-256-GCM AEAD encryption boundary
│   ├── storage/          # 134-byte binary envelope & atomic file persistence
│   ├── services/         # VaultService, Auth, CredentialService, Session, Settings, Clipboard
│   ├── models/           # Credential & VaultPayload domain models
│   └── ui/               # ApplicationController, LockedView, UnlockedView, SetupWizard, ThemeManager
│       └── setup/        # Multi-step QWizard onboarding pages
├── assets/               # Production assets (SecureVault.ico)
├── packaging/            # PyInstaller spec and Inno Setup installer scripts
│   ├── SecureVault.spec  # PyInstaller onedir windowed configuration
│   └── SecureVault.iss   # Inno Setup 6 installer script
├── tests/                # Pytest unit & integration test suites (378 tests)
├── scripts/              # Verification test harnesses
├── docs/                 # Architectural, security, and design specifications
├── main.py               # Application entry point (GUI launch + headless flags)
├── requirements.txt      # Runtime dependencies
├── requirements-dev.txt  # Dev/test dependencies
├── pyproject.toml        # Package metadata & pytest configuration
└── README.md             # Developer setup, principles, and packaging instructions
```

---

## Documentation Index

Comprehensive project specifications are maintained in the [`docs/`](docs/) directory:

- [AI Context & Handoff Guide](docs/AI_CONTEXT.md)
- [Current Project State](docs/CURRENT_STATE.md)
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Security Model](docs/SECURITY_MODEL.md)
- [Cryptographic Architecture](docs/CRYPTOGRAPHY.md)
- [Vault Data Format Specification](docs/DATA_FORMAT.md)
- [UI/UX Design Specification](docs/UI_DESIGN.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Testing Strategy & QA](docs/TESTING.md)
- [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Architecture Decision Records (ADRs)](docs/DECISIONS.md)

---

## License

Open Source — Planned under MIT or Apache 2.0 license upon v1.0.0 release.
