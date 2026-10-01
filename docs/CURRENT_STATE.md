# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M11 — Security Hardening`
- **Status**: **Implementation complete** (Verified with 362 Passing Tests)
- **Target Release**: Version 1.0.0 (Windows)
- **Previous Milestone**: `M10 — Clipboard Security` (Complete, verified)
- **Next Milestone**: `M12 — Packaging & Distribution`
- **Note on M9**: Milestone M9 (Password Generator) was permanently removed from the roadmap by user instruction.

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
  - Fixed M4 GUI integration bug: enforced non-None `DecryptedVault` propagation across signals and controller transitions.

### Milestone 5 (M5 — Credential CRUD, Encrypted Persistence & View/Edit UI)
- **Credential Model (`app/models/credential.py`, `app/models/__init__.py`)**:
  - Strictly defined entity containing exactly: `id`, `title`, `username`, `password`, `notes`.
  - Automated identity: generated unique UUID string per credential; users cannot manually specify or alter it.
  - Strict exclusions: no `type`, `category`, `tags`, or extraneous timestamps.
  - Safe representation: `Credential.__repr__` automatically redacts secret passwords to `'***'`.
  - Serialization / Deserialization: `to_dict()` and `from_dict()` preserving exact JSON schema.
- **Validation Engine (`app/core/validation.py`, `app/core/exceptions.py`)**:
  - Added `validate_credential(title, username, password, notes)` enforcing non-empty required fields.
  - Added domain exceptions: `CredentialError`, `CredentialNotFoundError`, `CredentialValidationError`, and `VaultLockedError`.
- **Vault Persistence Engine (`app/services/vault_service.py`)**:
  - Added `save_vault(self, vault=None)`: serializes updated payload JSON, re-encrypts under active in-memory DEK with fresh 12-byte CSPRNG nonce and 18-byte `AAD_PAYLOAD`, updates the frozen `VaultHeader` via `dataclasses.replace`, and persists atomically via temporary file and replace.
- **Credential Service (`app/services/credential_service.py`, `app/services/__init__.py`)**:
  - Implemented `CredentialService`:
    - `create_credential(title, username, password, notes)`
    - `get_credential(id)` -> returns `Credential | None`
    - `get_credential_or_raise(id)` -> raises `CredentialNotFoundError` if missing
    - `get_all_credentials()` -> returns `list[Credential]`
    - `update_credential(id, title, username, password, notes)`
    - `delete_credential(id)` -> removes item and persists
  - Bound to active `VaultService`; operations raise `VaultLockedError` if the vault session is locked.
  - Zero password logging enforced across all operations.
- **View & Edit UI Integration & Polish (`app/ui/unlocked_view.py`, `app/ui/app_window.py`)**:
  - `UnlockedView` upgraded with dynamic credential counter, smooth pixel-based scrolling (`ScrollPerPixel`), and session lock.
  - `CredentialCardWidget`: Individual card row displaying title, username, notes preview, and dedicated `[ View ]`, `[ Edit ]`, `[ Delete ]` buttons operating on that credential's ID.
  - `ViewCredentialDialog`: Read-only dialog displaying Title, Username, Password, Notes. Password is masked by default with a `[ Show ]` / `[ Hide ]` toggle button. No "type" field exists.
  - `EditCredentialDialog`: Editable form populated with existing values. Password is masked by default with a `[ Show ]` / `[ Hide ]` toggle. Preserves untouched original password when saving. Validates required fields and saves through `CredentialService.update_credential()`.
  - `AddCredentialDialog`: Modal creation dialog with field validation and masked password input.
  - **Delete Selected Removed**: Redundant bottom "Delete Selected" button removed entirely; per-card Delete button is the sole and clean deletion entrypoint.
  - **Delete Confirmation Dialog**: Shows warning modal (*"Are you sure you want to delete '{title}'? This action cannot be undone."*) with `Cancel` and `Delete` buttons before executing permanent deletion.
  - **Smooth Pixel Scrolling**: Configured `ScrollPerPixel` and vertical scrollbar single step on `credential_list` for fluid, non-jumping card scrolling.
  - Seamless data flow verified: `UI -> CredentialService -> DecryptedVault -> VaultService -> Encrypted .svault`.
- **Testing**: 216 tests passing across entire suite (62 M5 tests covering models, CRUD operations, persistence lifecycles, UI view/edit/card layout, delete confirmation, and smooth scrolling).

### Milestone 6 (M6 — Main Vault UI + Search)
- **Main Vault Layout Enhancements (`app/ui/unlocked_view.py`)**:
  - Upgraded `UnlockedView` to provide clean hierarchical layout:
    - Window title: `SecureVault — Vault Unlocked`
    - Header: `🔓 SecureVault — Unlocked`
    - Profile: `Profile: <b>{login_id}</b>`
    - Vault ID: `Vault ID: <code>{vault_id}</code>`
    - Search Bar row: `[ Search credentials... ] [ Clear ]`
    - Dynamic credential counter: `Stored Credentials: <b>{total}</b>` (or `Showing <b>{matched}</b> of <b>{total}</b> credentials`)
    - Credential list with smooth pixel scrolling (`ScrollPerPixel`)
    - Bottom action bar: `[ ➕ Add Credential ] [ 🔒 Lock Vault ] [ Exit ]`
- **In-Memory Credential Search**:
  - Live search on `textChanged` signal with zero debouncing latency.
  - Substring matching across `title`, `username`, and `notes`.
  - Case-insensitive search (`lower()`).
  - **CRITICAL SECURITY BOUNDARY**: The `password` field is strictly excluded from search operations and is never inspected or matched.
  - Read-only UI operation: search never alters vault state, never saves, and never triggers disk I/O.
- **Clear Search Controls**:
  - Native clear icon and dedicated `[ Clear ]` button resets input and immediately restores full credential list and counter.
- **Empty State Feedback**:
  - Empty Vault State (`total == 0`): displays `"No credentials yet. Add your first credential to get started."` with a direct `[ ➕ Add Credential ]` button.
  - No Search Results State (`total > 0`, `matched == 0`): displays `"No credentials found. Try a different search term."` while keeping bottom actions available.
- **Action & Identity Preservation**:
  - Filtered cards retain true `cred.id`; clicking `View`, `Edit`, or `Delete` operates strictly on the intended credential, never list indices.
  - Delete confirmation modal preserved on filtered cards.
  - Session lock clears search query text buffer.
- **Testing**: 233 automated tests passing across entire suite (17 new dedicated M6 tests in `tests/test_ui_search.py`).

### Milestone 7 (M7 — Session Management & Auto-Lock)
- **Session Manager Architecture (`app/services/session_manager.py`)**:
  - Implemented `SessionManager`, `SessionInactivityState`, and `ActivityEventFilter`.
  - State machine: `INACTIVE`, `ACTIVE`, `GRACE_PERIOD`, `COUNTDOWN`, `LOCKED`.
  - Timing model:
    - 15-second hidden grace period (`ACTIVITY_GRACE_SECONDS = 15`).
    - 2-minute visible countdown (`INACTIVITY_TIMEOUT_SECONDS = 120`).
    - Total inactivity before automatic lock: 2 minutes 15 seconds.
  - Reset Behavior:
    - Activity detected: typing (`KeyPress`), clicking (`MouseButtonPress`), scrolling (`Wheel`).
    - **CRITICAL SECURITY / UX BOUNDARY**: Mouse movement alone (`MouseMove`) strictly does NOT reset inactivity.
    - Any interaction resets the session, stops countdown, hides countdown label, and starts a fresh 15-second grace period.
- **Top-Right Auto-Lock Countdown UI & Header Alignment (`app/ui/unlocked_view.py`)**:
  - Unobtrusive `QLabel` placed in the top-right corner of the Unlocked View.
  - Positioned within a single-cell `QGridLayout` overlay on the header row: `header` is centered against the full window width (`550.0px`) while `countdown_label` is aligned to the top-right (`AlignRight | AlignVCenter`).
  - Hiding or showing the countdown label has zero effect on header geometry; the title remains centered at all times.
  - Hidden during active user interaction and throughout the 15-second grace period.
  - Appears after 15 seconds of inactivity displaying `Auto-lock: 02:00`.
  - Decrements once per second (`01:59`, `01:58`, ..., `00:01`, `00:00`).
  - Disappears immediately upon typing, clicking, or scrolling.
- **Login / LockedView Masked Password Enforcement (`app/ui/locked_view.py`)**:
  - Master password field on LockedView remains strictly masked (`EchoMode.Password`) with no "Show Password" checkbox.
- **Automatic & Manual Lock Unification**:
  - Reaches `00:00` -> emits `timeout_triggered` signal -> invokes existing `lock_vault` workflow.
  - Any open modals/dialogs (`AddCredentialDialog`, `EditCredentialDialog`, `ViewCredentialDialog`, etc.) are automatically dismissed.
  - Zeros in-memory DEK buffer and clears decrypted vault data.
  - Transitions to `LockedView` requiring master password re-entry.
  - Manual "Lock Vault" button and window close stop all timers and clean up event filters.
  - Zero sensitive data (keys, passwords, credentials) is ever stored in session/timer objects.
- **Testing**: 268 automated tests passing across entire suite (29 dedicated M7 tests in `tests/test_session_management.py`).
- **Manual Verification**: All manual verification steps (A through P) executed and verified.

### Milestone 8 (M8 — Settings + Theme)
- **Settings Service Architecture (`app/services/settings_service.py`)**:
  - Implemented `AppSettings` model and `SettingsService`.
  - Non-sensitive JSON persistence at `%LOCALAPPDATA%\SecureVault\settings.json`.
  - Atomic writes via `.tmp` file and `os.replace`.
  - Settings schema:
    - `"theme"`: `"dark"` | `"light"` (default: `"dark"`).
    - `"auto_lock_timeout"`: `120` | `300` | `600` | `900` seconds (default: `120`).
  - Validation with safe defaults fallback for missing or corrupted files.
  - Strict security boundary: `settings.json` contains zero keys, passwords, hashes, tokens, or credentials (`PROHIBITED_CONFIG_KEYS`).
  - The 15-second grace period (`ACTIVITY_GRACE_SECONDS = 15`) is strictly system-defined and NOT stored in settings.json.
- **Centralized Theme Management (`app/ui/theme.py`)**:
  - Implemented `ThemeManager` singleton providing application-wide `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
  - Supports exactly two themes: Dark and Light.
  - Immediate runtime switching without application restart via `ThemeManager.instance().apply_theme(...)`.
  - Saved theme is restored upon startup before any window is rendered to prevent visual flash.
  - Covers all UI areas: Main Vault, Locked View, Setup Wizard, Settings Dialog, Credential Cards, Dialogs, Search, Buttons, and Alerts.
- **Auto-Lock Timeout Customization**:
  - Configurable in Settings → Security: exactly four choices (2, 5, 10, 15 minutes).
  - Live session updates: changing timeout immediately updates active `SessionManager.set_countdown_seconds(...)` without restarting.
  - Grace period remains system-defined and invariant at 15 seconds.
  - M7 event detection (typing/clicks/scrolling reset, mouse movement alone does not reset) remains 100% intact.
- **Cryptographic Master Password Change (`app/services/vault_service.py`, `app/ui/settings_dialog.py`)**:
  - Form in Settings → Security with masked inputs: Current Password, New Password, Confirm New Password.
  - Validates current password against header KEK/DEK unwrap before any changes.
  - Re-wraps the SAME existing DEK under a fresh Argon2id KEK with a new 16-byte CSPRNG salt.
  - Preserves vault payload ciphertext, payload nonce, payload tag, and `vault_id` intact.
  - Atomic persistence to disk via temporary file and replace.
  - Intermediate key buffers zeroed via `zero_buffer`.
  - Displays required note: *"After successfully changing your master password, SecureVault will lock the vault and return you to the login screen. You must use your new master password to unlock the vault again."*
  - Automatically locks vault session and transitions to `LockedView` on success; requires new master password to unlock.
### Milestone 10 (M10 — Clipboard Security & Auto-Clear Watchdog)
- **Centralized Clipboard Service (`app/services/clipboard_service.py`)**:
  - Implemented `ClipboardService` with `copy_username()`, `copy_password()`, `copy_text()`.
  - Enforced system-defined, non-configurable 30-second cleanup timeout (`CLIPBOARD_CLEAR_TIMEOUT_SECONDS = 30`).
  - Strict clipboard ownership verification: checks `clipboard.text() == tracked_value` before clearing.
  - User clipboard protection: if the user copies unrelated text during the 30-second window, SecureVault leaves external text intact.
  - Overlapping copy resolution: subsequent copies immediately cancel previous timers and track the newest value.
  - Reject empty and whitespace values without modifying clipboard or arming timers.
  - Session lock integration: manual lock, auto-lock timeout, and master password change execute `clear_if_owned()`.
  - Application exit integration: `app.aboutToQuit` signal connected to `clear_if_owned()`.
  - Zero sensitive data logging (only non-sensitive events "SecureVault clipboard copy initiated" and "SecureVault clipboard cleanup completed" are logged).
  - Zero clipboard history, zero disk persistence, zero networking.
- **UI Integration (`app/ui/unlocked_view.py`, `app/ui/theme.py`)**:
  - `ViewCredentialDialog`: Added `[ Copy Username ]` and `[ Copy Password ]` buttons beside respective fields.
  - Password remains masked by default with Show/Hide toggle.
  - Non-blocking confirmation message: *"Username copied. Clipboard will clear in 30 seconds."* and *"Password copied. Clipboard will clear in 30 seconds."*.
  - `UnlockedView` displays non-sensitive copy confirmations and auto-cleared status.
  - Themed `QPushButton#CopyUsernameBtn` and `QPushButton#CopyPasswordBtn` in Dark and Light themes.
- **Testing**: 24 automated unit and UI tests in `tests/test_clipboard_service.py` and `tests/test_ui_clipboard.py`.
- **Manual Verification**: Script `scripts/verify_m10.py` verified all 27 Section 19 steps.

### Milestone 11 (M11 — Security Hardening)
- **Security Audit**: Completed a 27-area comprehensive audit of M0 through M10 implementations against `docs/THREAT_MODEL.md` (0 Critical, 0 High, 1 Medium, 2 Low, 3 Informational findings).
- **Deterministic KEK Memory Erasure (`SEC-M11-01` / M11.1)**:
  - Added `as_bytearray: bool = False` option to `derive_kek()` in `app/crypto/kdf.py`.
  - Refactored `VaultService.create_vault()`, `unlock_vault()`, and `change_master_password()` to store derived KEK material in mutable `bytearray` containers.
  - Guaranteed `zero_buffer()` execution inside `finally` blocks immediately upon completion or failure of DEK wrapping/unwrapping.
  - Converted to immutable `bytes(kek)` only at the exact point of invocation into cryptography's `AESGCM`.
- **Transient Password Buffer Zeroing (`SEC-M11-02` / M11.2)**:
  - In `app/crypto/kdf.py`, converted encoded master password to a mutable `bytearray` before passing to Argon2id CFFI.
  - Explicitly zeroed the transient mutable password buffer with `zero_buffer()` in `finally`.
  - Preserved documented limitations regarding CPython string immutability.
- **Atomic In-Memory State Updates (`SEC-M11-03` / M11.3)**:
  - Refactored `VaultService.save_vault()` to construct prepared payload and header copies separately.
  - In-memory `target_vault.payload["updated_at"]`, `header`, and `raw_json` are committed only *after* `write_vault_file()` returns successfully.
  - Any disk write or encryption failure leaves active in-memory session state completely unmodified, preventing memory-disk divergence.
- **Constant-Time Password Reuse Comparison (`SEC-M11-04` / M11.4)**:
  - Introduced `PasswordReuseError` inheriting from `InvalidPasswordInputError` in `app/core/exceptions.py`.
  - Hardened `change_master_password()` to use `hmac.compare_digest(cur_pwd_str, new_pwd_str)` to prevent timing side channels.
- **Security Regression Test Suite (`tests/test_m11_security_hardening.py`)**:
  - Implemented 9 dedicated regression tests verifying KEK zeroing, KDF password buffer zeroing, atomic save failure rollback, and constant-time reuse detection.
  - Total test suite count increased to 362 passing tests (100% pass rate).

### Application Icon Resource Integration (M13 Preparation)
- **Official Application Icon**: Integrated `assets/SecureVault.ico` (multi-resolution 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256).
- **Central Loading**: Configured `setup_application_icon()` in `app/ui/app_window.py` to apply icon globally to `QApplication.setWindowIcon()`.
- **Resource Path Resolution**: Added `get_asset_path()`, `get_app_icon_path()`, and `AppConfig.icon_path` in `app/core/config.py` with cross-platform and frozen-bundle compatibility.
- **Window Icon Inheritance**: Verified automatic propagation to `SetupWizard`, `LockedView`, `UnlockedView`, `SettingsDialog`, `ViewCredentialDialog`, and `EditCredentialDialog`.
- **Windows Taskbar Integration**: Configured `SetCurrentProcessExplicitAppUserModelID` for native Windows taskbar icon grouping.
- **Testing**: Added `tests/test_app_icon.py` (10 tests; total test suite: 372 tests passing).

---

## 3. What is Intentionally NOT Implemented in M11

In strict adherence to project boundaries and milestone separation:
- **No Architectural Redesign**: Envelope KEK/DEK design, Argon2id parameters, and AES-256-GCM AEAD construction are preserved.
- **No Format Changes**: Vault binary format (`.svault` 134-byte header) and AAD design remain strictly identical.
- **No False Memory Guarantees**: Acknowledged inherent CPython interpreter limitations regarding high-level immutable `str` objects.
- **No Feature Creep**: Zero password generators, cloud sync, SQLite, CSV export, or networking.

---

## 4. Current Task
Milestone M11 (Security Hardening) COMPLETE, tested, and verified (362 tests passing).

---

## 5. Next Task
Milestone M12 — Packaging & Distribution.

---

## 6. Known Issues / Unresolved Items
- **None**: All M11 hardening tasks implemented; 362/362 automated tests pass with 100% pass rate. Verification scripts `verify_m7.py`, `verify_m8.py`, and `verify_m10.py` pass cleanly.

---

## 7. Important Decisions Summary
- **ADR-001 through ADR-011**: Foundational architecture, GUI, offline, cryptographic, storage, and logging decisions.
- **ADR-012**: Zero-Verifier / KEK-Only Master Authentication.
- **ADR-013**: Decoupled AAD Envelope Architecture for Atomic Key Rotation.
- **ADR-014**: In-Memory Credential CRUD & Immediate Atomic Vault Re-Encryption.
- **ADR-015**: Event-Driven Inactivity Monitoring & Two-Stage Auto-Lock Lifecycle.
- **ADR-016**: Non-Sensitive Preferences Architecture, Centralized Dynamic Theming, and Cryptographic Master Password Rotation.
- **ADR-017**: Centralized Clipboard Security Service, Strict Ownership Verification, and Auto-Clear Watchdog.
- **ADR-018**: Deterministic Ephemeral Buffer Hygiene, In-Memory Save Atomicity, and Constant-Time Equality Hardening.


