# SecureVault — Development Roadmap

This document outlines the sequential development lifecycle for SecureVault Version 1.0.
Each milestone is discrete, testable, and gated by defined completion criteria.

---

## Milestone Overview

```
[M0: Architecture & Security] ──► [M1: Project Skeleton] ──► [M2: First-Run Wizard]
                                                                     │
[M5: Credential CRUD] ◄── [M4: Cryptographic Vault] ◄── [M3: Master Auth]
        │
        ▼
[M6: Main Vault UI] ──► [M7: Session & Auto-Lock] ──► [M8: Settings & Theme]
                                                               │
[M11: Hardening] ◄── [M10: Export & Clipboard] ◄── [M9: Password Gen]
        │
        ▼
[M12: Comprehensive Testing] ──► [M13: Windows Packaging] ──► [M14: Security Review & Release]
```

---

## Detailed Milestone Specifications

### M0 — Architecture & Security Design (CURRENT — READY TO FREEZE)
- **Objective**: Establish foundational security rules, cryptographic specifications, file formats, threat models, and architectural boundaries before writing code.
- **Key Deliverables**: 12 comprehensive documentation files in `docs/` and project `README.md`, including verified 134-byte binary header, master-password-independent `AAD_PAYLOAD`, and explicit threat boundaries.
- **Exit Criteria**: All architectural decisions approved; consistency pass complete; no implementation code or premature dependencies added.

### M1 — Project Skeleton & Documentation System
- **Objective**: Scaffold the production directory layout, dependency management (`pyproject.toml` / `requirements.txt`), linting/type-checking configurations (`ruff`, `mypy`), and development CLI entry points.
- **Key Deliverables**:
  - `app/` package structure (`app/core/`, `app/crypto/`, `app/storage/`, `app/ui/`, `app/services/`).
  - Configured virtual environment, pinned dependencies (`PySide6`, `cryptography`, `argon2-cffi`, `pytest`).
  - Working headless CLI stub and application launch smoke test.
- **Dependencies**: M0.

### M2 — First-Run Setup Wizard
- **Objective**: Implement the initial user onboarding flow in PySide6 for users launching the application without an existing vault (`UNINITIALIZED` state).
- **Key Deliverables**:
  - Welcome screen with explanation cards.
  - Security terms & "No Recovery Key" acknowledgment screen with required checkbox.
  - Master Password creation UI with real-time entropy/strength meter.
  - Wizard controller managing step transitions.
- **Dependencies**: M1.

### M3 — Master Authentication
- **Objective**: Build master password validation, Argon2id key derivation bridge, and unlock interface (`LOCKED` state).
- **Key Deliverables**:
  - `AuthenticationService` orchestrating Argon2id derivation (64 MiB RAM, t=3, p=4, 16B salt).
  - `LoginView` UI with auto-focus, mask toggle, and generic failure error banner.
  - Constant-time comparison safeguards and generic error handling.
- **Dependencies**: M2.

### M4 — Cryptographic Vault
- **Objective**: Implement the low-level cryptographic engine and binary envelope file storage.
- **Key Deliverables**:
  - `CryptoEngine`: AES-256-GCM AEAD encryption/decryption with decoupled AAD binding (`AAD_DEK` and `AAD_PAYLOAD`).
  - `VaultStorage`: Binary file reader/writer for 134-byte fixed header with atomic file swap semantics (`os.replace`).
  - Wrapped DEK envelope serialization and deserialization.
  - Integrity validation and tamper detection.
- **Dependencies**: M3.

### M5 — Credential CRUD
- **Objective**: Implement the in-memory vault domain model, JSON payload schema, and credential data management.
- **Key Deliverables**:
  - `CredentialItem` and `VaultPayload` dataclasses / models.
  - `VaultManager` implementing Create, Read, Update, Delete methods.
  - UUID generation and UTC ISO-8601 timestamp management.
  - Dirty state tracking and serialization hooks.
- **Dependencies**: M4.

### M6 — Main Vault UI + Search (Completed)
- **Objective**: Implement the primary unlocked vault dashboard with credential search and browsing.
- **Key Deliverables**:
  - Main vault layout with profile information, vault ID, and consistent SecureVault styling.
  - Search bar (`QLineEdit`) with clear action and live in-memory search filtering.
  - Case-insensitive substring matching against `title`, `username`, and `notes`.
  - Strict security boundary: `password` field is strictly non-searchable.
  - Dynamic credential counter (`Stored Credentials: X` / `Showing X of Y credentials`).
  - Useful empty states for empty vault and no-search-results conditions.
  - Preservation of credential identity across filtered View, Edit, and Delete actions.
  - Delete confirmation modal preservation and smooth pixel scrolling.
- **Dependencies**: M5.

### M7 — Session & Auto-Lock (Completed)
- **Objective**: Implement session inactivity management, grace period, auto-lock countdown, and automatic lock.
- **Key Deliverables**:
  - `SessionManager` managing inactivity lifecycle (`INACTIVE`, `ACTIVE`, `GRACE_PERIOD`, `COUNTDOWN`, `LOCKED`).
  - Inactivity model: 15-second hidden grace period (`ACTIVITY_GRACE_SECONDS = 15`) + 2-minute visible countdown (`INACTIVITY_TIMEOUT_SECONDS = 120`) = 2m15s total timeout.
  - Interaction filter: captures typing (`KeyPress`), clicking (`MouseButtonPress`), and scrolling (`Wheel`).
  - Mouse movement alone strictly ignored and does NOT reset timer.
  - Top-right unobtrusive countdown label (`Auto-lock: MM:SS`) in `UnlockedView` with independent single-cell overlay preserving title centering in all states.
  - Automatic lock unified with existing vault lock mechanism (zeroing DEK, closing modals, returning to `LockedView`).
  - Comprehensive 29-test suite in `tests/test_session_management.py`.
  - Manual verification completed across all test steps A through P.
- **Dependencies**: M6.

### M8 — Settings + Theme (Completed)
- **Objective**: Implement application preferences, persistent configuration, UI theming, and master password rotation.
- **Key Deliverables**:
  - `SettingsService` reading/writing non-sensitive JSON in `%LOCALAPPDATA%\SecureVault\settings.json`.
  - Strict enforcement of plaintext boundaries (`PROHIBITED_CONFIG_KEYS`: forbidden to store keys, passwords, hashes, tokens, or credentials).
  - Centralized `ThemeManager` with runtime switching between Dark and Light QSS themes without restart.
  - Configurable auto-lock timeout (2, 5, 10, 15 minutes) with live `SessionManager` update; system-defined 15-second grace period preserved.
  - "Change Master Password" workflow in Settings → Security: Argon2id KEK derivation, fresh salt, atomic re-wrapping of the active DEK (leaving payload untouched), auto-lock on completion.
  - Modal `SettingsDialog` with General and Security tabs.
  - 329 passing automated tests and automated verification script.
- **Dependencies**: M7.

### M9 — Password Generator (Permanently Removed)
- **Status**: Permanently removed from roadmap by user directive. Not implemented.

### M10 — Clipboard Security & Auto-Clear (Completed)
- **Objective**: Implement safe credential copying with auto-clear watchdog.
- **Key Deliverables**:
  - `ClipboardService` copying username and password values with temporary UI feedback and 30-second watchdog auto-clear (`CLIPBOARD_CLEAR_TIMEOUT_SECONDS = 30`).
  - Strict clipboard ownership verification: checks `clipboard.text() == tracked_value` before clearing.
  - Preserves user-replaced clipboard content; never overwrites or wipes external text.
  - Resolves overlapping copy operations by restarting timer and updating ownership state.
  - Immediate cleanup of owned content on session lock or application exit.
  - ViewCredentialDialog with `[ Copy Username ]` and `[ Copy Password ]` actions and non-blocking status feedback.
  - 353 passing automated tests across full test suite.
- **Dependencies**: M8.

### M11 — Security Hardening (Completed)
- **Objective**: Conduct defensive code hardening across the entire application stack.
- **Key Deliverables**:
  - Security audit across 27 areas confirming zero critical/high vulnerabilities and zero networking/telemetry.
  - Deterministic KEK memory zeroing via mutable `bytearray` and guaranteed `finally: zero_buffer()` across `create_vault()`, `unlock_vault()`, and `change_master_password()`.
  - Transient master password buffer zeroing in Argon2id KDF derivation (`app/crypto/kdf.py`).
  - Atomic in-memory state updates in `VaultService.save_vault()`, preventing state divergence on persistence failure.
  - Constant-time password reuse comparison using `hmac.compare_digest()` and `PasswordReuseError`.
  - 9 targeted security regression tests in `tests/test_m11_security_hardening.py` (362 tests passing total).
- **Dependencies**: M10.

### M12 — Testing
- **Objective**: Execute comprehensive unit, integration, and UI test suites.
- **Key Deliverables**:
  - 90%+ code coverage on cryptographic, storage, and session engines.
  - Tamper injection and corruption test suites.
  - Headless UI testing with `pytest-qt`.
  - Continuous Integration (CI) configuration for automated test runs.
- **Dependencies**: M11.

### M13 — Windows Packaging (Completed)
- **Objective**: Produce a standalone, reproducible Windows binary package and installer.
- **Key Deliverables**:
  - `packaging/SecureVault.spec`: Windowed onedir PyInstaller spec bundling `assets/SecureVault.ico` and excluding dev/test infrastructure.
  - `dist/SecureVault/SecureVault.exe`: Standalone 2.06 MB executable running without Python or virtualenv.
  - `packaging/SecureVault.iss`: Inno Setup 6 installer script generating `dist_installer/SecureVault-Setup-0.1.0.exe` (34.9 MB).
  - Explicit user data separation: application binaries install to `{autopf}\SecureVault`, while encrypted vault data lives strictly in `%LOCALAPPDATA%\SecureVault`.
  - Guaranteed uninstall data survival: verified that `%LOCALAPPDATA%\SecureVault` is strictly preserved upon application uninstall, and reopened upon reinstall.
  - Automated verification harnesses in `scripts/verify_m13_packaging.py` and `scripts/verify_m13_installer.py`.
- **Dependencies**: M11.

### M14 — Final Security Review + Open Source Release
- **Objective**: Final pre-release audit, licensing, and documentation polish.
- **Key Deliverables**:
  - Code audit against the Threat Model and Cryptographic specification.
  - Open-source license (MIT / Apache 2.0) and contribution guidelines.
  - Release notes, verification checksums, and GitHub Release v1.0.0 publication.
- **Dependencies**: M13.
