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
- `tests/test_ui_locked_view.py` (7 tests):
  - Verifies `LockedView` displays active `Login ID`.
  - Verifies password visibility toggle (Password <-> Normal echo mode).
  - Verifies empty password submission displays validation error without calling worker.
  - Verifies `AuthWorker(QThread)` executes KDF derivation off main thread, emits `unlock_successful`, and passes derived KEK.
  - Verifies failed derivation emits `unlock_failed` and displays user-friendly error.
  - Verifies that clicking `Reset Setup (Dev)` emits `reset_requested` and cleans up state.
  - Verifies `ApplicationController` routes uninitialized state to wizard and initialized state to locked view.
- `tests/test_flow.py`:
  - Full end-to-end integration test: uninitialized -> cancel -> complete setup -> locked view -> restart.

---

## 3. Future Test Suites (Scheduled per Roadmap)

- **M4 (Cryptographic Vault)**: AES-256-GCM AEAD round-trip, AAD binding, 134-byte fixed header packing, atomic replace, bit-flip tamper detection.
- **M5 (Credential CRUD)**: In-memory credential CRUD, search/filtering, JSON schema serialization.
- **M7 (Session & Auto-Lock)**: 10-minute inactivity timer expiration, activity event reset, lock memory purging.
- **M10 (Clipboard & Export)**: 30-second clipboard watchdog clearing, CSV export with warning.

---

## 4. Test Execution

All tests are executed using pytest:
```powershell
# Run full test suite
.venv\Scripts\pytest.exe -v
```
*Current test status: 108 passed, 0 failed.*
