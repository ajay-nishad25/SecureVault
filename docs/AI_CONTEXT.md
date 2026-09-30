# SecureVault — AI Agent Context & Handoff Guide

> **PRIMARY DIRECTIVE**: Read this file first, then inspect [CURRENT_STATE.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md) before continuing or touching any code.

---

## 1. Project Purpose
SecureVault is an open-source, completely offline, zero-cloud desktop password manager. It allows users to store, manage, search, and generate credentials locally within a single encrypted binary file (`vault.svault`), requiring no internet connectivity, accounts, or remote servers.

---

## 2. Technology Stack & Platform
- **Language**: Python 3.11+ (Runtime: Python 3.11.4 in `.venv/`)
- **GUI Framework**: PySide6 (Qt 6 for Python)
- **Cryptography**: `cryptography` (AES-256-GCM AEAD), `argon2-cffi` (Argon2id KDF), standard `secrets` CSPRNG (to be wired in M3/M4)
- **Testing**: `pytest`
- **Platform**: Windows 10/11 64-bit first (`%LOCALAPPDATA%\SecureVault\`); portable design for Linux.

---

## 3. Package Structure
```text
SecureVault/
├── app/
│   ├── __init__.py       # Central version definition (__version__ = "0.1.0")
│   ├── core/             # AppConfig, Safe Logging, Domain Exceptions
│   ├── crypto/           # Cryptographic primitives boundary (M3/M4)
│   ├── storage/          # Binary envelope & atomic file persistence boundary (M4)
│   ├── services/         # Clipboard watchdog & auto-lock services boundary (M7/M10)
│   ├── models/           # CredentialItem & VaultPayload domain models (M5)
│   └── ui/               # PySide6 desktop views & themes (M2/M6/M8)
├── tests/                # Pytest unit & integration test suites
├── docs/                 # Architectural, security, and design specifications
├── main.py               # Minimal application entry point & CLI verification
├── requirements.txt      # Runtime dependencies (PySide6)
├── requirements-dev.txt  # Dev/test dependencies (pytest)
├── pyproject.toml        # Package metadata & pytest configuration
└── README.md             # Developer setup, principles, and roadmap
```

---

## 4. Milestone Status
- **Current Milestone**: `M1 — Project Skeleton & Development Foundation` (Implementation Complete / Ready for Review).
- **Next Milestone**: `M2 — First-Run Setup Wizard`.
- *Do not begin M2 or write application UI/business logic without explicit user instruction.*

---

## 5. Critical Inviolable Rules
1. **Never Invent Custom Cryptography**: Use only standard primitives from `cryptography` and `argon2-cffi`.
2. **Never Implement Prematurely**: Follow [DEVELOPMENT_ROADMAP.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DEVELOPMENT_ROADMAP.md) sequentially. Do not bundle future milestone features.
3. **Never Log Sensitive Secrets**: Master passwords, keys, and credentials must never be printed or logged. `SafeLogFilter` actively redacts known secret patterns.
4. **Never Store Secrets in Config**: `settings.json` and `AppConfig` are strictly for non-sensitive UI settings.
5. **Never Introduce Network Dependencies**: No `urllib`, `requests`, `aiohttp`, `socket`, or cloud SDKs.
6. **No Overclaims**: Python memory clearing is best-effort (`bytearray` overwrite), not guaranteed physical erasure.
