# SecureVault

**SecureVault** is an open-source, completely offline desktop password manager built with Python and PySide6. It is designed for users who demand absolute privacy, zero-cloud architecture, and robust local cryptographic security.

---

## Current Status

- **Current Milestone**: `M3 — Master Authentication` (Complete / Ready for Review)
- **Active Version**: `0.1.0`
- **Application State**: The multi-step First-Run Setup Wizard, input validation rules, and Argon2id Master Key Derivation (`Master Password + Salt -> Argon2id -> 32-byte KEK`) are fully implemented and verified with non-blocking UI integration. The full encrypted `.svault` file and AES-256-GCM vault encryption remain deferred to Milestone M4.

---

## Technical Stack

- **Language**: Python 3.11+ (Tested on Python 3.11.4)
- **GUI Toolkit**: PySide6 (Qt 6 for Python)
- **Cryptographic Libraries**: `argon2-cffi` (Argon2id KDF), standard `secrets` CSPRNG, `cryptography` (AES-256-GCM AEAD for M4)
- **Test Runner**: `pytest` (108 passing tests)
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
# Install runtime dependencies (PySide6)
pip install -r requirements.txt

# Or install all development and testing dependencies (PySide6 + pytest)
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
# Run all 108 unit and GUI integration tests
pytest

# Run tests with verbose output
pytest -v
```

---

## Package Structure

```text
SecureVault/
├── app/
│   ├── __init__.py       # Central version definition (__version__ = "0.1.0")
│   ├── core/             # AppConfig, Safe Logging, Domain Exceptions, Validation
│   ├── crypto/           # Cryptographic primitives boundary (M3/M4)
│   ├── storage/          # Binary envelope & atomic file persistence boundary (M4)
│   ├── services/         # InitializationService, Clipboard watchdog (M10), Auto-lock (M7)
│   ├── models/           # CredentialItem & VaultPayload domain models (M5)
│   └── ui/               # ApplicationController, LockedView, SetupWizard
│       └── setup/        # Multi-step QWizard onboarding pages
├── tests/                # Pytest unit & integration test suites (79 tests)
├── docs/                 # Architectural, security, and design specifications
├── main.py               # Application entry point (GUI launch + headless flags)
├── requirements.txt      # Runtime dependencies (PySide6)
├── requirements-dev.txt  # Dev/test dependencies (pytest)
├── pyproject.toml        # Package metadata & pytest configuration
└── README.md             # Developer setup, principles, and roadmap
```

---

## Documentation Index

Comprehensive project specifications are maintained in the [`docs/`](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/) directory:

- [AI Context & Handoff Guide](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/AI_CONTEXT.md)
- [Current Project State](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md)
- [Project Overview](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/PROJECT_OVERVIEW.md)
- [System Architecture](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/ARCHITECTURE.md)
- [Security Model](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/SECURITY_MODEL.md)
- [Cryptographic Architecture](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CRYPTOGRAPHY.md)
- [Vault Data Format Specification](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DATA_FORMAT.md)
- [UI/UX Design Specification](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/UI_DESIGN.md)
- [Threat Model](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/THREAT_MODEL.md)
- [Testing Strategy & QA](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/TESTING.md)
- [Development Roadmap](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DEVELOPMENT_ROADMAP.md)
- [Architecture Decision Records (ADRs)](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DECISIONS.md)

---

## License

Open Source — Planned under MIT or Apache 2.0 license upon v1.0.0 release.
