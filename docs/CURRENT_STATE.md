# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M4 — Cryptographic Vault`
- **Status**: **Implementation Complete / Ready for Review**
- **Target Release**: Version 1.0.0 (Windows)
- **Next Milestone**: `M5 — Credential CRUD & In-Memory Operations`

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
  - Implemented `KDFParameters` dataclass strictly adhering to M0 cryptographic specifications:
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
  - Zero-Verifier Architecture: No password verifier, hash file, or persistent auth marker is written. Authentication success in M3 represents successful key derivation; M4 connects this derived KEK to unwrap the encrypted DEK.
  - Transient In-Memory Session Management: Provides `clear_session()` with best-effort zeroing (`kek_bytes[:] = b'\x00' * len(kek_bytes)`).

### Milestone 4 (M4 — Cryptographic Vault Implementation)
- **AES-256-GCM Primitives (`app/crypto/encryption.py`)**:
  - DEK Generation: `generate_dek() -> bytes` producing 32 uniform random bytes via `secrets.token_bytes(32)`.
  - Nonce Generation: `generate_nonce(size: int = 12) -> bytes` ensuring 96-bit CSPRNG uniqueness.
  - DEK Wrapping / Unwrapping: `wrap_dek(kek, dek, aad_dek)` and `unwrap_dek(kek, nonce, wrapped_dek, tag, aad_dek)` using AES-256-GCM under the derived KEK.
  - Payload Encryption / Decryption: `encrypt_payload(dek, plaintext, aad_payload)` and `decrypt_payload(dek, nonce, ciphertext, tag, aad_payload)`.
  - Memory Hygiene: `zero_buffer(buf)` providing in-place mutable zeroing.
- **134-byte Fixed Binary Header (`app/storage/vault_format.py`)**:
  - Exact 134-byte (`0x86`) static header layout conforming byte-by-byte to `docs/DATA_FORMAT.md`.
  - Big-Endian byte order for all multi-byte integers (`FORMAT_VERSION`, `KDF_MEMORY`, `KDF_TIME`, `KDF_PARALLEL`, `PAYLOAD_LEN`).
  - Strict validation of MAGIC (`b"SVAULT01"`), format version (`1`), KDF ID (`1`), and length fields.
  - Golden test fixture ensuring byte offsets cannot regress silently.
  - Exact AAD slicing:
    - `AAD_DEK`: 38 bytes (`file_bytes[0x00:0x26]`).
    - `AAD_PAYLOAD`: 18 bytes (`file_bytes[0x00:0x0A] || file_bytes[0x62:0x6A]`).
- **Atomic Persistence (`app/storage/vault_file.py`)**:
  - Implemented `write_vault_file` using temporary file (`vault.svault.tmp`), buffer flush, `os.fsync`, and atomic `os.replace`.
  - Implemented `read_vault_file` with truncation checks and exact `PAYLOAD_LEN` matching against header metadata.
- **Vault Orchestration (`app/services/vault_service.py`)**:
  - `create_vault`: Creates empty JSON envelope, generates DEK, wraps under KEK, encrypts payload, writes atomic file.
  - `unlock_vault`: Reads file, extracts KDF parameters, derives KEK, unwraps DEK (natural wrong-password detection), decrypts payload, parses JSON envelope into active `DecryptedVault`.
  - `lock_vault`: In-place zeroing of mutable DEK buffer and dereferencing of decrypted payload.
- **UI Integration (`app/ui/setup/wizard.py`, `app/ui/locked_view.py`, `app/ui/unlocked_view.py`, `app/ui/app_window.py`)**:
  - Setup Wizard now creates the real encrypted `vault.svault` file upon completing onboarding.
  - `LockedView` uses background `AuthWorker(QThread)` to unlock and decrypt vault without freezing the event loop.
  - Emits `vault_unlocked(DecryptedVault)` carrying the concrete decrypted session object to `ApplicationController._on_vault_unlocked(vault)`.
  - `UnlockedView` displays real session metadata (`vault_id`, stored item count) from the active `DecryptedVault`.
  - `ApplicationController` routes `UNINITIALIZED -> SetupWizard -> LOCKED -> UnlockedView -> LOCKED`, locking active session on exit.
  - Fixed M4 GUI integration bug: removed legacy transitional fallback in `AuthWorker.run()` that emitted `vault=None`, enforced strict `DecryptedVault` propagation, updated UI feedback message to "Vault decrypted and authenticated successfully.", and added missing vault file detection and recovery guidance.
- **Files Added / Modified**:
  - *Added*: `app/crypto/encryption.py`, `app/storage/vault_format.py`, `app/storage/vault_file.py`, `app/services/vault_service.py`, `app/ui/unlocked_view.py`, `tests/test_encryption.py`, `tests/test_vault_format.py`, `tests/test_vault_service.py`.
  - *Modified*: `requirements.txt`, `pyproject.toml`, `app/crypto/__init__.py`, `app/storage/__init__.py`, `app/services/__init__.py`, `app/core/exceptions.py`, `app/services/initialization.py`, `app/ui/setup/wizard.py`, `app/ui/locked_view.py`, `app/ui/app_window.py`, `tests/test_ui_locked_view.py`, `tests/test_flow.py`.
- **Testing**: 154 tests passing (46 new tests covering AES-256-GCM primitives, 134-byte golden binary layout, file tampering/corruption, atomic persistence, security secrecy, wrong-password rejection, and DecryptedVault propagation to UnlockedView).

---

## 3. What is Intentionally NOT Implemented in M4

In strict adherence to the milestone boundaries:
- **Credential CRUD (Create, Read, Update, Delete)**: Deferred to M5.
- **Credential Management UI**: Deferred to M5/M6.
- **Password Generator**: Deferred to M6.
- **Auto-Lock Timers**: Deferred to M7.
- **Search & Filtering**: Deferred to M8.
- **Clipboard Management**: Deferred to M10.
- **CSV Export**: Deferred to M10.
- **Password Rotation UI**: Deferred to M11 (underlying AAD format is already decoupled in M4).

---

## 4. Current Task
M4 review and verification.

---

## 5. Next Task
M5 — Credential CRUD & In-Memory Operations.

---

## 6. Known Issues / Unresolved Items
- **None**: All M4 cryptographic vault deliverables are implemented and tested with 100% pass rate (152/152 passing tests).

---

## 7. Important Decisions Summary
- **ADR-001 through ADR-011**: Foundational language, GUI, offline, cryptographic, storage, and logging decisions.
- **ADR-012**: Zero-Verifier / KEK-Only Master Authentication.
- **ADR-008 & M4 Architecture**: Decoupled AAD design (`AAD_PAYLOAD` excludes salt and KDF fields) guarantees future master password rotation does not require re-encrypting the vault payload.
