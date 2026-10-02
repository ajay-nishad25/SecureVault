# SecureVault

**SecureVault** is an open-source, completely offline desktop password manager built with Python and PySide6. It is designed for users who demand absolute privacy, zero-cloud architecture, and robust local cryptographic security.

---

## Official Releases & Repository

- **Repository**: [https://github.com/ajay-nishad25/SecureVault](https://github.com/ajay-nishad25/SecureVault)
- **Releases**: [https://github.com/ajay-nishad25/SecureVault/releases](https://github.com/ajay-nishad25/SecureVault/releases)
- **Current Windows Release**: `SecureVault-Setup-0.1.0.exe` (Windows 10/11 64-bit)

---

## Key Features & Security Architecture

### Core Features (v0.1.0)
- **Credential Storage**: Securely store and manage usernames/login IDs, passwords, and notes.
- **Credential Search**: Instant real-time search filtering across stored entries.
- **Entry Management**: View, edit, and delete credentials with immediate state updates.
- **Secure Clipboard**: Automatic clipboard clearing after copying sensitive fields with a countdown watchdog.
- **Configurable Auto-Lock**: Two-stage inactivity timeout that locks the session when unattended.
- **Master Password Change**: Safely re-wrap the vault Data Encryption Key (DEK) without re-encrypting the underlying database entries.
- **Theme Selection**: Polished Dark and Light themes with dynamic switching.
- **Windows Installer**: Packaged standard Windows installer (`SecureVault-Setup-0.1.0.exe`) and standalone executable.

### Security Architecture
- **Completely Local & Offline**: Zero cloud storage, zero remote backend, zero telemetry, and no network dependencies.
- **No SQLite**: Employs a flat encrypted vault binary payload with atomic file writes to ensure data integrity and prevent corruption.
- **Argon2id Key Derivation**: Master password derives a Key Encryption Key (KEK) using memory-hard Argon2id.
- **AES-256-GCM Envelope Encryption**: Vault contents are encrypted with a random 256-bit Data Encryption Key (DEK). The DEK is encrypted with the KEK and stored in a fixed 134-byte binary envelope (`vault.svault`).
- **Zero Master Password Storage**: Master password is never stored on disk or logged.
- **No Password Recovery**: No backdoors, recovery keys, or escrow in v0.1.0. If the master password is permanently lost, the vault cannot be recovered.
- **Memory Hygiene**: Best-effort deterministic ephemeral memory wiping for sensitive in-memory cryptographic material.

### Product Boundaries & Current Scope
To maintain an uncompromising security posture and a minimal attack surface, the following boundaries apply to v0.1.0:
- **No Cloud Synchronization**: Vault data never leaves the local system.
- **No Browser Extensions or Background Daemons**: No open network ports, IPC sockets, or browser extension hooks.
- **No Password Generator / Suggestion Tool**: Not included in v0.1.0; users manage and supply their own passwords.
- **No CSV / Plaintext Export**: Plaintext bulk export is intentionally not implemented.
- **No Password Recovery**: No recovery key or password reset mechanism exists.
- **Platform Support**: Windows-first (Windows 10/11 64-bit). Linux and macOS support are planned and coming soon.
- **Mobile Support**: No mobile application currently exists.

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

## Microsoft Defender SmartScreen Notice

SecureVault is a new Windows application and is actively pursuing trusted code signing.

- Digital signing does not guarantee that Microsoft Defender SmartScreen will immediately stop displaying reputation warnings.
- As a newly published application, initial releases may trigger SmartScreen unknown publisher or reputation warnings until sufficient community reputation is established over time.
- Consistent signing across consecutive releases and legitimate distribution allow reputation to build over time.
- Users should always obtain installers directly from the official [SecureVault Releases](https://github.com/ajay-nishad25/SecureVault/releases) page.

---

## Privacy Statement

SecureVault is designed to operate entirely locally and offline.

> "This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it."

The application contains no telemetry, analytics, crash-reporting pings, remote backend services, or automatic background network checkers.

---

## Code Signing Policy

Free code signing provided by SignPath.io, certificate by SignPath Foundation.

SecureVault is an open-source project. Official Windows releases are intended to be digitally signed using the SignPath Foundation code-signing service. SecureVault is applying to use the SignPath Foundation code-signing service for official Windows releases.

- **Open-Source Artifacts**: Windows release artifacts are built transparently from the project's public source repository and release/build configuration.
- **Release Signing**: Code signing is intended for official Windows release artifacts (executables and installers).
- **Manual Approval**: Signing requests require manual approval prior to release publication.
- **Maintainer Responsibility**: The project maintainer is responsible for the project's signing and release approval process.
- **Identity Consistency**: The signing identity should remain consistent across releases where possible.
- **Official Releases**: Users should obtain official Windows releases from the project's official GitHub repository release page: [https://github.com/ajay-nishad25/SecureVault/releases](https://github.com/ajay-nishad25/SecureVault/releases).

### Signing Roles

Release-signing responsibilities for SecureVault are managed by the project maintainer:
- **Project Maintainer**: Ajay Nishad (`ajay-nishad25`) is responsible for repository source integrity, initiating release builds, and authorizing code-signing requests through the SignPath pipeline.
- If SignPath requires specific role separation during onboarding, the role structure remains compatible with SignPath Foundation's actual configuration rather than claiming that multiple independent people exist.

---

## Package Structure

```text
SecureVault/
├── LICENSE               # MIT License
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
└── README.md             # Project documentation, security, and packaging guides
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

SecureVault is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the complete license text.

