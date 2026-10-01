# SecureVault — Testing Strategy & Quality Assurance

## 1. Testing Philosophy & Test Pyramid

SecureVault's testing architecture enforces high-reliability standards appropriate for security software:

```
                ▲
               / \
              /   \
             / UI  \        [30%] PySide6 Wizard & View State Tests (Headless Offscreen)
            /-------\
           /  Integ  \      [25%] End-to-End Onboarding & Lifecycle Flows
          /-----------\
         /    Unit     \    [45%] Config, Logging, Exceptions, Validation, State Service
        /---------------\
```

- **Zero Network Ingestion**: No test may make external network requests.
- **Hermetic Isolation**: Tests run against isolated, temporary file paths (`tmp_path`) that clean up automatically.
- **Fail-Secure Assertions**: Security boundaries (prohibited config keys, password non-persistence, validation rules) are validated with negative test cases.
- **Headless Qt Testing**: Desktop PySide6 UI tests run via `QT_QPA_PLATFORM=offscreen`, allowing reliable execution in continuous integration and headless environments without a physical display.

---

## 2. Active Test Suites (Implemented in M1 & M2)

### 2.1 Package & Entry Point Tests
- `tests/test_package.py`:
  - Validates `__version__ = "0.1.0"` defined centrally.
  - Verifies importability of all core packages (`core`, `crypto`, `storage`, `services`, `models`, `ui`).
- `tests/test_entrypoint.py`:
  - Verifies `main.py` headless startup (`--headless`) and config verification (`--check-config`).
  - Verifies that default invocations properly call the GUI entry point.

### 2.2 Core Infrastructure Tests
- `tests/test_config.py`:
  - Verifies `AppConfig` default paths (`%LOCALAPPDATA%\SecureVault\`).
  - Verifies `validate_safe_setting_key` accepts safe UI settings (`theme`, `auto_lock_minutes`).
  - Verifies `validate_safe_setting_key` rejects sensitive keys (`password`, `master_password`, `kek`, `dek`, `secret`, `token`).
- `tests/test_logging.py`:
  - Verifies `get_logger` namespacing under `securevault.*`.
  - Verifies that `SafeLogFilter` actively redacts password and secret patterns in log strings.
  - Verifies that operational messages are preserved.
- `tests/test_exceptions.py`:
  - Verifies that all domain exceptions inherit from `SecureVaultError`.

### 2.3 Validation Tests
- `tests/test_validation.py`:
  - **Login ID**: Validates length (3–64 chars), character whitelist (alphanumeric, `.`, `_`, `-`, `@`), rejects empty/whitespace, and rejects reserved system names (`admin`, `root`, `superuser`, `null`).
  - **Master Password**: Verifies minimum length (8 chars), rejects empty strings, and rejects mismatched entries.
  - **Password Strength**: Validates advisory estimation scoring across empty, weak, medium, and strong inputs.

### 2.4 Initialization & State Persistence Tests
- `tests/test_initialization.py`:
  - Verifies fresh state is detected as `UNINITIALIZED`.
  - Verifies `initialize(login_id)` persists `init_state.json` and transitions to `LOCKED`.
  - **Security Scan**: Explicitly reads `init_state.json` to verify that passwords, password hashes, and cryptographic keys are NEVER persisted.
  - Verifies `reset()` cleanly unlinks the state file and returns to `UNINITIALIZED`.

### 2.5 PySide6 Setup Wizard UI Tests
- `tests/test_ui_wizard.py`:
  - Verifies sequence of all 7 wizard pages.
  - Verifies `AcknowledgementPage` disables progression until the no-recovery checkbox is ticked.
  - Verifies `LoginIdPage` dynamically validates input and gates the Next button.
  - Verifies `MasterPasswordPage` validates matching passwords, toggles visibility, and gates the Next button.
  - Verifies that `clear_sensitive_inputs()` wipes password line edit fields.
  - Verifies `FinalWarningPage` requires confirmation checkbox.
  - Verifies that wizard cancellation (`reject()`) leaves the application uninitialized.
  - Verifies that wizard completion (`accept()`) persists valid state, emits completion signals, and clears password fields.

### 2.6 Key Derivation Function (KDF) Tests (M3)
- `tests/test_kdf.py` (19 tests):
  - **Salt Generation**: Verifies 16-byte length, non-constant random output across calls, and rejection of invalid salt lengths.
  - **KDF Parameter Validation**: Validates `KDFParameters` constructor enforcement (positive memory, time, parallelism, hash length, salt length) and rejection of invalid values.
  - **Key Derivation Correctness**: Verifies output is exactly 32 bytes (256-bit KEK).
  - **Determinism**: Verifies `derive_kek(P, S, params) == derive_kek(P, S, params)`.
  - **Input Sensitivity**: Verifies that different passwords, different salts, or different parameters produce distinct 32-byte keys.
  - **Input Validation**: Verifies rejection of empty passwords (str and bytes) and malformed salt lengths (`InvalidPasswordInputError`, `InvalidSaltError`).
  - **Production Parameter Execution**: Executes real M0 production parameters (`m=65536 KiB, t=3, p=4`) to verify compatibility and timing.

### 2.7 Authentication Service Tests (M3)
- `tests/test_authentication_service.py` (7 tests):
  - **Lifecycle**: Verifies initialization with default or custom salt and KDF parameters.
  - **Key Derivation Flow**: Verifies `authenticate(password)` returns `AuthenticationResult(success=True)` with 32-byte KEK.
  - **Session Management**: Verifies `active_kek` retention and in-place zeroing upon `clear_session()`.
  - **Input Validation**: Verifies error handling and clean `AuthenticationResult(success=False)` on empty passwords or parameter violations.
  - **No Secret Logging**: Uses `caplog` to assert that master password and raw KEK hex are NEVER emitted to application logs.

### 2.8 View Controller & UI Integration Tests
- `tests/test_ui_locked_view.py` (9 tests):
  - Verifies `LockedView` displays active `Login ID`.
  - Verifies password visibility toggle (Password <-> Normal echo mode).
  - Verifies empty password submission displays validation error without calling worker.
  - Verifies successful password unlock emits `vault_unlocked` Signal containing a non-None `DecryptedVault` with valid `vault_id` and `items`.
  - Verifies wrong password does NOT emit `vault_unlocked`, displays user error, and leaves vault locked.
  - Verifies `ApplicationController` transitions to `UnlockedView` with valid `DecryptedVault` on success, rejects wrong password without view transition, and transitions back to `LockedView` upon locking.
  - Verifies clicking `Reset Setup (Dev)` emits `reset_requested` and cleans up state and vault file.
  - Verifies `ApplicationController` routes uninitialized state to wizard and initialized state to locked view.
- `tests/test_flow.py`:
  - Full end-to-end integration test: uninitialized -> cancel -> complete setup -> locked view -> wrong password rejection -> correct password unlock to `UnlockedView(vault=DecryptedVault)` -> lock back to `LockedView`.

### 2.9 AES-256-GCM Encryption Tests (M4)
- `tests/test_encryption.py` (18 tests):
  - **DEK Generation**: Validates 32-byte key length and CSPRNG randomness across calls.
  - **Nonce Generation**: Enforces 12-byte (96-bit) length, CSPRNG randomness, and rejection of invalid sizes.
  - **Key Wrapping**: Verifies AES-256-GCM round-trip wrapping/unwrapping of DEK under KEK and AAD_DEK.
  - **Tag Verification**: Verifies rejection of wrong KEK, tampered ciphertext, tampered tag, tampered nonce, and tampered AAD.
  - **Payload Encryption**: Validates AES-256-GCM encryption/decryption round-trip, ciphertext privacy (plaintext absent), and tamper rejection.
  - **Memory Zeroing**: Validates in-place mutable buffer zeroing.

### 2.10 Vault Binary Format & Golden Header Tests (M4)
- `tests/test_vault_format.py` (12 tests):
  - **Size Invariant**: Verifies exact 134-byte (`0x86`) static header size.
  - **Golden Header Fixture**: Byte-by-byte offset verification matching `docs/DATA_FORMAT.md`:
    - `0x00-0x07`: `MAGIC` (`b'SVAULT01'`)
    - `0x08-0x09`: `FORMAT_VERSION` (`1`)
    - `0x0A`: `KDF_ID` (`1`)
    - `0x0B-0x0E`: `KDF_MEMORY` (`65536`)
    - `0x0F-0x12`: `KDF_TIME` (`3`)
    - `0x13-0x14`: `KDF_PARALLEL` (`4`)
    - `0x15`: `SALT_LEN` (`16`)
    - `0x16-0x25`: `SALT` (16B)
    - `0x26-0x31`: `DEK_NONCE` (12B)
    - `0x32-0x51`: `WRAPPED_DEK` (32B)
    - `0x52-0x61`: `DEK_TAG` (16B)
    - `0x62-0x69`: `PAYLOAD_LEN` (8B)
    - `0x6A-0x75`: `PAYLOAD_NONCE` (12B)
    - `0x76-0x85`: `PAYLOAD_TAG` (16B)
    - `0x86`: Payload ciphertext start offset.
  - **Round-Trip Fidelity**: Verifies serialization and deserialization across all fields.
  - **AAD Slicing**: Validates exact 38-byte `AAD_DEK` and 18-byte `AAD_PAYLOAD` extraction.
  - **Validation & Rejection**: Verifies rejection of bad magic, unsupported versions, bad KDF ID, and truncated headers.

### 2.11 Vault Service & Persistence Tests (M4/M5)
- `tests/test_vault_service.py` (16 tests):
  - **Vault Creation & Unlock**: Verifies creation of `.svault` file, file size calculation (134 + payload), and unlock with correct password.
  - **Natural Wrong-Password Detection**: Verifies that incorrect passwords trigger authenticated DEK unwrap failure and raise `AuthenticationError`.
  - **Input Bounds**: Verifies empty passwords raise `InvalidPasswordInputError`.
  - **Corruption Rejection**: Verifies fail-secure rejection of corrupted magic, corrupted wrapped DEK, corrupted DEK tag, corrupted payload ciphertext, corrupted payload tag, and truncated payload bytes.
  - **Atomic Persistence**: Verifies `.tmp` file is safely renamed and no temporary file remains.
  - **Security Secrecy Scan**: Verifies that the `.svault` file does NOT contain master passwords, raw DEK bytes, raw KEK bytes, or plaintext JSON strings.
  - **Session Locking**: Verifies that `lock()` zeroes mutable DEK buffers and clears payload data.
  - **Payload Re-Encryption (`save_vault`)**: Verifies updating payload content re-encrypts under active DEK and persists changes atomically.

### 2.12 Credential CRUD & Persistence Tests (M5)
- `tests/test_credential_model.py` (11 tests):
  - **Validation**: Enforces non-empty required fields (`title`, `username`, `password`) and optional `notes`.
  - **Identity**: Verifies automatic unique UUID generation.
  - **Schema Fidelity**: Verifies `to_dict` and `from_dict` strictly preserve schema (`id`, `title`, `username`, `password`, `notes`) with no extra fields or types.
  - **Masked Representation**: Verifies `__repr__` redacts passwords to `'***'`.
- `tests/test_credential_service.py` (19 tests):
  - **CREATE**: Valid credential creation, UUID uniqueness, required field validation, atomic disk persistence, and zero password logging.
  - **READ**: Retrieval by ID, listing all entries, and clean unknown ID handling (`None` / `CredentialNotFoundError`).
  - **UPDATE**: Modifying title, username, password, and notes; ID immutability; invalid update rejection; disk persistence.
  - **DELETE**: Safe deletion by ID, item count reduction, disk persistence, and unknown ID rejection.
  - **Locked Vault Guard**: Enforces `VaultLockedError` on all CRUD operations if vault session is locked.
- `tests/test_credential_persistence.py` (4 tests):
  - **Full Lifecycles**: `Create -> Lock -> Unlock -> Reload`, `Create -> Update -> Lock -> Unlock -> Reload`, `Create -> Delete -> Lock -> Unlock -> Reload`.
  - **Ciphertext Privacy**: Verifies that credential passwords, titles, and usernames are completely absent from raw `.svault` file bytes on disk.
- `tests/test_ui_unlocked_view.py` (4 tests):
  - Verifies dynamic credential count, list rendering, Add Credential dialog validation, delete action, and session lock wiping.
- `tests/test_ui_view_edit.py` (9 tests):
  - **View Dialog**: Verifies display of Title, Username, Password, Notes; verifies read-only enforcement; verifies password masked by default; verifies `[ Show ]` / `[ Hide ]` toggle; verifies zero "type" field; verifies closing leaves vault unchanged.
  - **Edit Dialog**: Verifies form population with existing values; verifies password masked by default with `[ Show ]` / `[ Hide ]` toggle; verifies field validation keeping dialog open on failure; verifies Cancel leaves data unchanged.
  - **Untouched Password Preservation**: Verifies that editing only title/notes preserves the existing password without asterisks or placeholder overwrites.
  - **Full Update**: Verifies updating all fields retains the same ID with no duplicates.
  - **Persistence Across Lock/Unlock**: Verifies `Create -> Edit -> Lock -> Unlock -> Read` preserves updated fields across re-encryption.
  - **Multiple Credential Independence**: Verifies operating on one credential (View GitHub, Edit Google, Delete Google) does not alter or corrupt independent credentials (LinkedIn, GitHub).
  - **Card Signals**: Verifies `CredentialCardWidget` emits view, edit, and delete signals mapped to specific credential IDs.

### 2.13 Main Vault UI & In-Memory Search Tests (M6)
- `tests/test_ui_search.py` (17 tests):
  - **Empty Search**: Verifies empty/whitespace query returns full credential list and full counter.
  - **Title Matching**: Verifies exact and partial substring matching against title.
  - **Username Matching**: Verifies exact and partial substring matching against username.
  - **Notes Matching**: Verifies exact and partial substring matching against notes.
  - **Case-Insensitivity**: Verifies matching is case-insensitive across uppercase, lowercase, and mixed queries.
  - **Strict Password Non-Searchability**: Verifies passwords are never matched or exposed via search (searching for plaintext password yields 0 results).
  - **Empty States**: Verifies empty vault message vs no-search-results message.
  - **Clear Search**: Verifies `[ Clear ]` button clears search input and restores full list and counter.
  - **Zero-Persistence Guarantee**: Verifies search never triggers `save_vault` or modifies file on disk.
  - **ID & Action Preservation**: Verifies filtered cards retain exact `cred.id`; View, Edit, and Delete operate on the true credential identity.
  - **Delete Confirmation**: Verifies confirmation modal remains active on filtered credentials.
  - **Multi-Credential Lifecycle**: Full sequence `Search -> View -> Edit -> Clear` verifying independent credentials remain intact.
  - **Lock Reset**: Verifies locking active session resets and clears search field buffer.
  - **Smooth Scrolling Configuration**: Verifies `ScrollPerPixel` and single step 16px are preserved.
- `tests/test_ui_window_size.py` (6 tests):
  - **Dimension Constants**: Verifies centralized `WINDOW_WIDTH = 1100` and `WINDOW_HEIGHT = 780`.
  - **Setup Wizard Sizing**: Verifies `SetupWizard` initializes at 1100 × 780 px.
  - **Locked View Sizing**: Verifies `LockedView` initializes at 1100 × 780 px.
  - **Unlocked View Sizing**: Verifies `UnlockedView` initializes at 1100 × 780 px.
  - **Consistent Screen Transitions**: Verifies transitions across `SetupWizard -> LockedView -> UnlockedView -> LockedView` maintain 1100 × 780 px.
  - **Centering Utility**: Verifies `center_window` positions top-level widgets correctly without error.

### 2.14 Session Management & Auto-Lock Tests (M7)
- `tests/test_session_management.py` (29 tests):
  - **Session Lifecycle**: Verifies session starts only upon unlocking; inactive in LockedView; stopping session clears state.
  - **Interaction Detection**:
    - Typing (`KeyPress`) resets inactivity and restarts 15s grace.
    - Clicking (`MouseButtonPress`) resets inactivity and restarts 15s grace.
    - Scrolling (`Wheel`) resets inactivity and restarts 15s grace.
    - **Mouse Movement Invariant**: Explicitly verifies `MouseMove` does NOT reset inactivity.
  - **Timing & Visibility**:
    - Countdown hidden during active user interaction.
    - Countdown hidden throughout 15-second grace period.
    - Countdown becomes visible after 15 seconds.
    - Countdown begins at exactly `02:00` (120s) and decrements once per second (`01:59`, `01:58`, etc.).
    - Interaction during countdown immediately hides it and restarts 15-second grace period.
    - Countdown reaching `00:00` triggers `timeout_triggered` signal.
  - **Header Alignment Invariant**:
    - Verifies "🔓 SecureVault — Unlocked" header remains at exact horizontal center (`window.width() / 2`) across all timer visibility states.
  - **Locking & Security**:
    - Automatic lock triggers existing vault lock mechanism and memory wiping.
    - Master password required again to re-enter vault.
    - Manual "Lock Vault" button immediately cancels all timers and hides countdown.
    - Window close stops timers and cleans up Qt event filters.
    - Zero sensitive data (passwords, keys, credentials) stored in `SessionManager`.
  - **UI Controls Integration**:
    - Search typing resets session.
    - Credential list scrolling resets session.
    - Card View/Edit/Delete interactions reset session.
    - Open modal dialogs (`AddCredentialDialog`, `EditCredentialDialog`, `ViewCredentialDialog`) dismissed automatically on auto-lock timeout.

---

## 3. Future Test Suites (Scheduled per Roadmap)

- **M8 (Settings & Theming)**: Settings persistence, configurable auto-lock duration, dark/light theme switching.
- **M10 (Clipboard Security)**: 30-second clipboard watchdog clearing.

---

## 4. Test Execution

All tests are executed using pytest:
```powershell
# Run full test suite
.\.venv\Scripts\python.exe -m pytest -v
```
*Current test status: 268 passed, 0 failed.*
