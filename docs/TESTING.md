# SecureVault — Testing Strategy & Quality Assurance

## 1. Testing Philosophy & Test Pyramid

SecureVault's testing architecture enforces high-reliability standards appropriate for security software:

```
                ▲
               / \
              /   \
             / UI  \        [10%] Headless PySide6 GUI & Signal Tests (pytest-qt)
            /-------\
           /  Integ  \      [30%] End-to-End Vault Lifecycle & Storage Integration
          /-----------\
         /    Unit     \    [60%] Cryptography, KDF, CRUD, Session Engine, Settings
        /---------------\
```

- **Zero Network Ingestion**: No test may make external network requests.
- **Hermetic Isolation**: Tests run against isolated, temporary file paths (`tmp_path`) that clean up automatically.
- **Fail-Secure Assertions**: Cryptographic failure paths (wrong key, corrupt tag, truncated envelope, modified AAD) must explicitly raise predictable domain exceptions and never return partial data.

---

## 2. Test Suite Specifications (To Be Implemented in M12)

### 2.1 Cryptographic & KDF Tests (`tests/test_crypto.py`)
- **Argon2id Key Derivation**:
  - Verify deterministic derivation given fixed password, salt, and parameters.
  - Verify that differing salts produce orthogonal keys.
  - Verify performance metrics (execution time within expected 200ms–800ms desktop range).
- **AES-256-GCM AEAD Round-Trip**:
  - Test encryption followed by successful decryption of arbitrary byte payloads.
  - Verify 12-byte nonce uniqueness across 10,000 generated nonces.
  - Verify that ciphertext length matches payload length + 16-byte tag.
- **Associated Authenticated Data (AAD) Validation**:
  - Verify that modifying 1 byte of `AAD_DEK` (38-byte public header) causes DEK decryption failure.
  - Verify that modifying 1 byte of `AAD_PAYLOAD` (18 bytes: `MAGIC` + `FORMAT_VERSION` + `PAYLOAD_LEN`) causes payload decryption failure.
  - Verify that re-wrapping the DEK with a new salt and new KEK leaves `AAD_PAYLOAD` unchanged, ensuring payload decrypt remains valid without re-encrypting the payload.
- **Tamper Detection & Bit-Flipping**:
  - Flip 1 bit in ciphertext -> assert `InvalidTag` / `DecryptionError`.
  - Flip 1 bit in auth tag -> assert failure.
  - Flip 1 bit in nonce -> assert failure.
  - Truncate ciphertext by 1 byte -> assert failure.
- **Wrong Password Rejection**:
  - Derive key with wrong password -> assert decryption failure without partial disclosure.

---

### 2.2 Vault Storage & Binary Envelope Tests (`tests/test_storage.py`)
- **Envelope Packing & Parsing**:
  - Verify exact 134-byte fixed header layout and byte offsets (`0x00 - 0x85`).
  - Verify serialization of header (magic bytes `b'SVAULT01'`, format version `1`, KDF tuning, salt, wrapped DEK, payload metadata).
  - Verify deserialization matches original parameters.
  - Reject invalid magic bytes (`b'INVALID\x00'`).
  - Reject unsupported format versions (`version > 1`).
- **Atomic Save Mechanics**:
  - Verify that saving writes to `vault.svault.tmp` before replacing `vault.svault`.
  - Test simulated crash/permission error during save: verify original vault remains uncorrupted.
- **Storage Path Resolution**:
  - Verify correct path resolution on Windows (`%LOCALAPPDATA%\SecureVault\vault.svault`).
  - Verify directory creation if `%LOCALAPPDATA%\SecureVault\` does not exist.

---

### 2.3 Authentication & Session Tests (`tests/test_auth_session.py`)
- **Vault Unlock Lifecycle**:
  - Correct master password transitions session state from `LOCKED` to `UNLOCKED`.
  - Incorrect master password retains `LOCKED` state.
- **Inactivity Timeout**:
  - Fast-forward virtual clock (using time mocks): verify session locks after 10 minutes of simulated idle time.
  - Simulate user activity event: verify inactivity timer resets to 10 minutes.
- **Manual Lock & Memory Purging**:
  - Calling `lock()` resets session state to `LOCKED`.
  - Assert that in-memory DEK is set to `None`.
  - Assert that in-memory credential objects are emptied.
- **Master Password Change**:
  - Re-wrap DEK with new master password (new salt, new KEK, new DEK nonce/tag).
  - Lock vault, re-open with new master password -> assert success.
  - Attempt unlock with old master password -> assert failure.
  - Assert that payload ciphertext bytes and payload auth tag are identical before and after password change.

---

### 2.4 Credential CRUD Tests (`tests/test_vault_manager.py`)
- **Creation**: Add new credential item -> assert assigned UUID4, valid UTC timestamps.
- **Retrieval**: Retrieve entry by UUID -> assert all fields intact.
- **Update**: Modify username/notes -> assert `updated_at` timestamp advances.
- **Deletion**: Delete item -> assert removed from collection and search results.
- **Search & Filtering**:
  - Query by title substring (case-insensitive).
  - Query by username substring.
  - Filter by category and tags.
  - Filter by favorite status.

---

### 2.5 Settings Manager Tests (`tests/test_settings.py`)
- **Allowed Fields**:
  - Verify loading and saving of `theme`, `auto_lock_minutes`, `clipboard_clear_seconds`.
- **Strict Plaintext Security Boundary**:
  - Assert that `settings.json` never serializes passwords, KEK, DEK, or vault contents under any condition.

---

### 2.6 Clipboard Security Tests (`tests/test_clipboard.py`)
- **Copy with Countdown**:
  - Copy password -> verify OS clipboard receives string.
  - Advance time by 30 seconds -> verify OS clipboard is cleared.
- **Watchdog Protection**:
  - Copy password from SecureVault.
  - User copies arbitrary text ("hello world") from another app after 10 seconds.
  - Advance time to 30 seconds -> assert clipboard is NOT cleared (user's new text preserved).

---

### 2.7 Plaintext Export Tests (`tests/test_export.py`)
- **CSV Formatting**:
  - Verify generated CSV contains columns: `Title,Username,Password,Category,Tags,Notes`.
  - Assert that master password is NEVER present in the export output.
  - Verify handling of quotes, commas, and newlines in notes.
- **Warning & Auth Enforcement**:
  - Verify export requires explicit confirmation and password re-authentication before writing output.

---

## 3. Tooling & Test Automation Framework

- **Test Runner**: `pytest`
- **Coverage Tool**: `pytest-cov` (target: >= 90% coverage for crypto, storage, and core managers)
- **GUI Testing**: `pytest-qt` (allows headless testing of Qt signals, slots, and widgets without opening visible windows)
- **Type Checking**: `mypy --strict`
- **Linting & Code Style**: `ruff`
