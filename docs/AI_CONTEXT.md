# SecureVault — AI Agent Context & Handoff Guide

> **PRIMARY DIRECTIVE**: Read this file first, then inspect [CURRENT_STATE.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md) before continuing or touching any code.

---

## 1. Project Purpose
SecureVault is an open-source, completely offline, zero-cloud desktop password manager. It allows users to store, manage, search, and generate credentials locally within a single encrypted binary file (`vault.svault`), requiring no internet connectivity, accounts, or remote servers.

---

## 2. Technology Stack & Platform
- **Language**: Python 3.11+ (Runtime: Python 3.11.4 in `.venv/`)
- **GUI Framework**: PySide6 (Qt 6 for Python)
- **Cryptography**: `argon2-cffi` (Argon2id KDF), standard `secrets` CSPRNG, `cryptography` (AES-256-GCM AEAD, key wrapping, payload encryption)
- **Testing**: `pytest` (233 passing tests)
- **Platform**: Windows 10/11 64-bit first (`%LOCALAPPDATA%\SecureVault\`); portable design for Linux.

---

## 3. Package Structure
```text
SecureVault/
├── app/
│   ├── __init__.py       # Central version definition (__version__ = "0.1.0")
│   ├── core/             # AppConfig, Safe Logging, Domain Exceptions, Validation
│   ├── crypto/           # Argon2id KDF (kdf.py) & AES-256-GCM (encryption.py)
│   ├── storage/          # 134-byte binary header (vault_format.py) & atomic I/O (vault_file.py)
│   ├── services/         # VaultService, AuthenticationService, InitializationService, CredentialService
│   ├── models/           # Credential domain model (id, title, username, password, notes)
│   └── ui/               # ApplicationController, LockedView, UnlockedView, SetupWizard, View/Edit Dialogs
│       └── setup/        # Multi-step QWizard onboarding pages
├── tests/                # Pytest unit & integration test suites (233 tests)
├── docs/                 # Architectural, security, and design specifications
├── main.py               # Application entry point (GUI launch + headless flags)
├── requirements.txt      # Runtime dependencies (PySide6, argon2-cffi, cryptography)
├── requirements-dev.txt  # Dev/test dependencies (pytest)
├── pyproject.toml        # Package metadata & pytest configuration
└── README.md             # Developer setup, principles, and roadmap
```

---

## 4. Milestone Status
- **Completed Milestones**:
  - `M0 — Architecture & Security Design` (Complete)
  - `M1 — Project Skeleton & Development Foundation` (Complete)
  - `M2 — First-Run Setup Wizard` (Complete)
  - `M3 — Master Authentication Foundation` (Complete)
  - `M4 — Cryptographic Vault Implementation` (Complete)
  - `M5 — Credential CRUD, Encrypted Persistence & View/Edit UI` (Complete)
  - `M6 — Main Vault UI + Search` (Complete / Ready for Review)
- **Next Milestone**: `M7 — Session Security & Auto-Lock`
- **Location of M6 Main Vault & Search Layer**:
  - `app/ui/unlocked_view.py`: `UnlockedView` with search bar (`QLineEdit`), live in-memory filtering (`title`, `username`, `notes`), password exclusion security boundary, counter, empty states, and card list integration.
  - `tests/test_ui_search.py`: Comprehensive automated search and UI tests.
- *Do not begin M7 without user instruction.*

---

## 5. Critical Inviolable Rules
1. **Never Invent Custom Cryptography**: Use only standard primitives from `cryptography` and `argon2-cffi`.
2. **Never Implement Prematurely**: Follow [DEVELOPMENT_ROADMAP.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DEVELOPMENT_ROADMAP.md) sequentially.
3. **Never Log Sensitive Secrets**: Master passwords, keys, and credentials must never be printed or logged. `SafeLogFilter` actively redacts secret patterns.
4. **Never Store Secrets in Config or State Markers**: `settings.json` and `init_state.json` store only non-sensitive metadata.
5. **Never Introduce Network Dependencies**: No `urllib`, `requests`, `aiohttp`, `socket`, or cloud SDKs.
6. **No Overclaims**: Python memory clearing is best-effort (`bytearray` overwrite), not guaranteed physical erasure.
