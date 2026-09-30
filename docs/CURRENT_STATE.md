# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M3 — Master Authentication`
- **Status**: **Implementation Complete / Ready for Review**
- **Target Release**: Version 1.0.0 (Windows)
- **Next Milestone**: `M4 — Cryptographic Vault`

---

## 2. Completed Work

### Milestone 0 (M0 — Architecture & Security Design)
- **Architecture Design**: Defined component boundaries across GUI, Auth, Session, Vault, Crypto, Storage, Settings, and Clipboard managers (`docs/ARCHITECTURE.md`).
- **Security Model**: Documented trust boundaries, assets, persistence inventory, session lifecycle, and explicit limitations (`docs/SECURITY_MODEL.md`).
- **Cryptographic Design**: Defined Argon2id KDF parameters and AES-256-GCM AEAD encryption with two-tier KEK/DEK hierarchy (`docs/CRYPTOGRAPHY.md`).
- **Vault Format Design**: Designed verified 134-byte fixed binary envelope and master-password-independent AAD (`docs/DATA_FORMAT.md`).
- **Threat Model**: Documented STRIDE-based threat matrix separating mitigated threats from host-level realities (`docs/THREAT_MODEL.md`).
- **UI Design**: Detailed 11-screen user flow, keyboard shortcuts, and session states (`docs/UI_DESIGN.md`).
- **Testing Strategy**: Defined test pyramid and verification criteria (`docs/TESTING.md`).
- **Development Roadmap**: Established M0 through M14 roadmap (`docs/DEVELOPMENT_ROADMAP.md`).
- **Architecture Decisions**: Documented ADR-001 through ADR-010 (`docs/DECISIONS.md`).

### Milestone 1 (M1 — Project Skeleton & Development Foundation)
- **Python Project Environment**: Established local virtual environment (`.venv/`) on Python 3.11.4.
- **Dependency Management**: Established clear separation with `requirements.txt` (`PySide6>=6.5.0`), `requirements-dev.txt` (`pytest>=7.4.0`), and standardized `pyproject.toml`.
- **Package Structure**: Scaffolded clean architecture packages matching M0 boundaries (`app/core/`, `app/crypto/`, `app/storage/`, `app/services/`, `app/models/`, `app/ui/`).
- **Safe Configuration & Logging**: Built `AppConfig` and `SafeLogFilter` with automatic secret redaction (`docs/DECISIONS.md#ADR-011`).
- **Exception Hierarchy**: Built domain exception tree (`SecureVaultError`, `ConfigurationError`, `StorageError`, `SecurityError`, `ValidationError`).

### Milestone 2 (M2 — First-Run Setup Wizard)
- **First-Run Detection**: Implemented `InitializationService` tracking `UNINITIALIZED`, `LOCKED`, and `UNLOCKED` states.
- **Setup Wizard UI**: Created 7-step PySide6 `SetupWizard` (`QWizard`):
  1. *Welcome*: Local-first, offline intro without exaggerated claims.
  2. *Security Architecture*: Core principles (local custody, zero backdoors, no cloud sync in v1).
  3. *No-Recovery Acknowledgement*: Mandatory checkbox with Next button gating.
  4. *Login ID*: Non-secret user identifier with character, length, and reserved name validation.
  5. *Master Password*: Masked input, show/hide toggle, match validation, and advisory local strength meter.
  6. *Final Warning*: Summary of parameters with mandatory confirmation checkbox.
  7. *Completion*: Success notice and transition to `LOCKED` state.
- **Non-Sensitive Initialization State**: Persisted `init_state.json` containing only safe metadata (`initialized`, `login_id`, `created_at`, `format_version`). Zero passwords, hashes, or keys are stored.
- **Cancellation Handling**: Setup cancellation creates zero state files and wipes transient password inputs.
- **Locked State Transition**: Created `LockedView` placeholder showing profile ID and locked status, with dev reset capability.
- **Application Controller**: Built `ApplicationController` orchestrating `UNINITIALIZED -> SetupWizard -> LockedView` and `INITIALIZED -> LockedView`.
- **Testing**: Built 79 passing unit and headless Qt integration tests verifying all validation rules, page completion gates, cancellation, state file safety, and end-to-end onboarding lifecycle.

### Milestone 3 (M3 — Master Authentication Foundation)
- **Argon2id KDF Implementation (`app/crypto/kdf.py`)**:
  - Implemented `KDFParameters` data class strictly adhering to M0 cryptographic specifications:
    - `memory_cost = 65536` KiB (64 MiB)
    - `time_cost = 3` iterations
    - `parallelism = 4` threads
    - `salt_length = 16` bytes (128-bit)
    - `hash_length = 32` bytes (256-bit KEK)
  - Implemented explicit `KDFParameters.fast_for_testing()` (`m=1024, t=1, p=1`) separated cleanly to avoid weakening production defaults.
  - Implemented `generate_salt(length: int = 16) -> bytes` using Python's `secrets.token_bytes`.
  - Implemented `derive_kek(password: str | bytes, salt: bytes, parameters: KDFParameters) -> bytes` using `argon2.low_level.hash_secret_raw(..., type=Type.ID)` returning raw 32-byte key material.
  - Added strict parameter and input validation with custom exceptions (`InvalidPasswordInputError`, `InvalidSaltError`, `InvalidKDFParametersError`, `AuthenticationError`).
- **Authentication Service Abstraction (`app/services/authentication.py`)**:
  - Implemented `AuthenticationService` defining the security boundary:
    `UI -> AuthenticationService -> KDF -> 32-byte KEK`.
  - Zero-Verifier Architecture: No password verifier, hash file, or persistent auth marker is written. Authentication success in M3 represents successful key derivation; M4 will use this derived KEK to attempt unwrapping the encrypted DEK.
  - Transient In-Memory Session Management: Provides `clear_session()` with best-effort zeroing (`kek_bytes[:] = b'\x00' * len(kek_bytes)`).
- **Asynchronous UI Unlocking (`app/ui/locked_view.py`)**:
  - Enhanced `LockedView` with master password entry field, show/hide visibility toggle, and "Unlock Vault" action.
  - Created `AuthWorker(QThread)` to perform CPU/memory-intensive Argon2id derivation off the Qt main event loop, preventing UI freezes while maintaining clean thread boundaries.
  - Clear user feedback: informs user that KEK was successfully derived and ready for M4 encrypted vault unwrapping.
- **Files Added / Modified**:
  - *Added*: `app/crypto/kdf.py`, `tests/test_kdf.py`, `app/services/authentication.py`, `tests/test_authentication_service.py`
  - *Modified*: `requirements.txt`, `pyproject.toml`, `app/crypto/__init__.py`, `app/services/__init__.py`, `app/core/exceptions.py`, `app/ui/locked_view.py`, `app/ui/app_window.py`, `tests/test_ui_locked_view.py`
- **Testing**: 108 tests passing (29 new tests covering KDF determinism, salt randomness, input validation, service lifecycle, thread execution, and UI signal emissions).

---

## 3. What is Intentionally NOT Implemented in M3

In strict adherence to the milestone boundaries:
- **AES-256-GCM Vault Encryption**: Deferred to M4.
- **DEK Generation & Key Wrapping**: Deferred to M4.
- **`.svault` Binary File Serialization/Deserialization**: Deferred to M4.
- **Credential Storage & CRUD**: Deferred to M5.
- **Auto-Lock Timers**: Deferred to M7.
- **Clipboard Management**: Deferred to M10.
- **Persistent Password Verifier / Hash Database**: Explicitly prohibited by architecture (Zero-Verifier design, see ADR-012).

---

## 4. Current Task
M3 review and verification.

---

## 5. Next Task
M4 — Cryptographic Vault (AES-256-GCM, 134-byte binary header, DEK wrapping, atomic persistence).

---

## 6. Known Issues / Unresolved Items
- **None**: All M3 master authentication deliverables are implemented and tested with 100% pass rate (108/108 passing tests).

---

## 7. Important Decisions Summary
- **ADR-001 through ADR-011**: Foundational language, GUI, offline, cryptographic, storage, and logging decisions.
- **ADR-012: Zero-Verifier / KEK-Only Master Authentication**: SecureVault deliberately does NOT store a password hash or verifier on disk. Vault unlocking relies strictly on the mathematical ability of the derived KEK to decrypt the wrapped DEK in M4.
