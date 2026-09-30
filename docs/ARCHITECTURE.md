# SecureVault — System Architecture

## 1. Architectural Philosophy

SecureVault is built on five core architectural principles:
1. **Layered Separation of Concerns**: Strict boundaries between layers (the UI never interacts directly with cryptographic primitives; the storage layer never inspects decrypted credentials).
2. **Zero-Trust Persistence**: The persistence layer never handles unencrypted credentials; files on disk are opaque ciphertext envelopes with authenticated metadata.
3. **Transient In-Memory State**: Plaintext credentials reside in memory only when a session is unlocked and are actively dereferenced upon lock or termination.
4. **Offline Isolation**: No network stacks, background analytics, external telemetry, or remote communication sockets.
5. **Deterministic Atomic Operations**: Vault mutations follow atomic write-to-temp-then-rename semantics to prevent corruption from unexpected power loss or crashes.

---

## 2. High-Level Component Diagram

```
+-------------------------------------------------------------------------+
|                               GUI Layer                                 |
|  - MainWindow       - LoginView          - VaultView     - SettingsView |
|  - CreateEditModal  - PasswordGenerator  - ClipboardBar  - Dialogs      |
+--------------------+---------------------+--------------------+---------+
                     |                     |                    |
                     v                     v                    v
+--------------------+----+  +-------------+------+  +----------+---------+
|  Authentication Layer   |  |   Session Manager    |  |  Clipboard Manager |
| - Password validation   |  | - Session state      |  | - OS clipboard copy|
| - Key derivation bridge |  | - Inactivity timer   |  | - 30s auto-clear   |
| - Password change auth  |  | - Lock / Unlock      |  | - Content watchdog |
+--------------------+----+  +-------------+------+  +--------------------+
                     |                     |
                     v                     v
+--------------------+---------------------+------------------------------+
|                             Vault Manager                               |
| - In-memory decrypted credential collection                             |
| - CRUD operations (Create, Read, Update, Delete)                        |
| - Search, filtering, and sorting engine                                 |
| - Change tracking (dirty state) & serialization trigger                 |
+--------------------+------------------------------------+---------------+
                     |                                    |
                     v                                    v
+--------------------+----+                  +------------+---------------+
|   Cryptography Layer    |                  |      Settings Manager      |
| - Argon2id KDF          |                  | - Non-sensitive UI prefs   |
| - AES-256-GCM AEAD      |                  | - Theme & timeout configs  |
| - Nonce & salt gen      |                  | - Strict plaintext boundary|
| - Best-effort zeroing   |                  +----------------------------+
+--------------------+----+
                     |
                     v
+--------------------+----+
|      Storage Layer      |
| - %LOCALAPPDATA% path   |
| - Binary file read/write|
| - Atomic replace        |
+-------------------------+
```

---

## 3. Component Responsibilities & Boundaries

### 3.1 GUI Layer (`app.ui`)
- **Technology**: PySide6 (Qt 6 for Python).
- **Responsibilities**:
  - Render user interface screens and dialogs.
  - Capture user events (mouse movement, keypresses) to notify the Session Manager of active interactions.
  - Route user commands (login, lock, add credential, copy password, export CSV) to controller/manager services.
  - Display sanitized error messages without leaking internal exceptions or cryptographic parameters.
- **Boundaries**:
  - The UI layer does **not** perform cryptographic operations, file system reads/writes, or direct credential serialization.
  - It interfaces solely with the `AuthenticationLayer`, `SessionManager`, `VaultManager`, `ClipboardManager`, and `SettingsManager`.

### 3.2 Authentication Service (`app.services.authentication`)
- **Responsibilities**:
  - Provide a clean boundary between UI and cryptographic operations:
    ```text
    UI (LockedView)
          ↓ (AuthWorker QThread)
    AuthenticationService
          ↓
    Argon2id KDF (app.crypto.kdf)
          ↓
    32-byte KEK (Key Encryption Key)
    ```
  - Validate master password complexity rules and input constraints prior to invoking KDF.
  - Coordinate with the Cryptography Layer (`app.crypto.kdf`) to derive the 32-byte Key Encryption Key (KEK) using Argon2id and the vault's salt.
  - Manage in-memory KEK retention and provide `clear_session()` with best-effort zeroing of mutable key buffers.
  - Coordinate with M4 to attempt AES-256-GCM decryption of the vault's Data Encryption Key (DEK).
  - Return clear, sanitized `AuthenticationResult` structures to the GUI without disclosing internal exceptions, timing, or oracle leaks.
- **Boundaries**:
  - Does not manage PySide6 widgets or UI dialogs directly.
  - Operates purely in-memory; maintains **Zero-Verifier Architecture** (never writes password hashes or verifiers to disk; see ADR-012).
  - Executes long-running Argon2id KDF operations off the main Qt event loop via `AuthWorker(QThread)` in the UI layer to maintain desktop UI responsiveness.

### 3.3 Session Manager (`app.core.session`)
- **Responsibilities**:
  - Maintain session state: `UNINITIALIZED`, `LOCKED`, `UNLOCKED`.
  - Enforce the inactivity timeout (default: 10 minutes).
  - Listen for activity reset signals dispatched from the GUI event filter.
  - Execute the lock sequence:
    1. Instruct Vault Manager to release decrypted records.
    2. Instruct Cryptography Layer to purge ephemeral in-memory keys (with best-effort zeroing of mutable buffers).
    3. Instruct Clipboard Manager to clear any active credential data.
    4. Trigger UI transition back to the `LoginView`.
  - Handle application shutdown cleanup (closing application requires authentication on reopen).
- **Boundaries**:
  - Operates purely in-memory; does not persist session tokens or cache credentials across application restarts.

### 3.4 Vault Manager (`app.core.vault`)
- **Responsibilities**:
  - Maintain the active in-memory repository of credential items while unlocked.
  - Provide CRUD APIs: `create_item`, `get_item`, `update_item`, `delete_item`, `list_items`.
  - Provide fast querying and text matching across titles, usernames, categories, and notes.
  - Track whether the vault has unsaved modifications ("dirty" state).
  - Prepare normalized JSON payload structures for encryption by the Cryptography Layer and persistence by the Storage Layer.
- **Boundaries**:
  - Does not directly write to the file system; delegates encrypted payloads to the Storage Layer.
  - Does not manage cryptographic primitives; delegates encryption/decryption to the Cryptography Layer.

### 3.5 Cryptography Layer (`app.crypto`)
- **Responsibilities**:
  - Wrap vetted cryptographic libraries (`argon2-cffi`, `cryptography`).
  - Execute Argon2id key derivation using standardized parameters (memory, iterations, parallelism, salt).
  - Perform authenticated symmetric encryption and decryption using AES-256-GCM.
  - Generate cryptographically secure random bytes for salts, nonces, and keys using the OS CSPRNG (`secrets` module).
  - Provide best-effort memory zeroing helpers (`bytearray` overwrite) for sensitive mutable buffers.
- **Boundaries**:
  - Strictly independent of the GUI, file paths, and application domain models.
  - Operates exclusively on raw byte buffers (`bytes`, `bytearray`).

### 3.6 Storage Layer (`app.storage`)
- **Responsibilities**:
  - Resolve canonical storage paths (`%LOCALAPPDATA%\SecureVault\vault.svault` on Windows, `~/.local/share/securevault/vault.svault` on Linux).
  - Read and write binary envelopes containing headers, metadata, and ciphertexts.
  - Implement atomic write semantics:
    1. Write to a temporary file (`vault.svault.tmp`) in the target directory.
    2. Flush and synchronize file buffers (`os.fsync`).
    3. Atomically replace the destination file using `os.replace`.
- **Boundaries**:
  - Agnostic to vault contents. Treats the encrypted vault payload as an opaque byte stream.

### 3.7 Settings Manager (`app.core.settings`)
- **Responsibilities**:
  - Store and load non-sensitive user preferences:
    - Interface theme (`system`, `dark`, `light`).
    - Auto-lock timeout duration (1 to 60 minutes).
    - Clipboard auto-clear timeout (10 to 120 seconds).
    - Window dimensions and layout preferences.
  - Save preferences as standard formatted JSON in `%LOCALAPPDATA%\SecureVault\settings.json`.
- **Strict Plaintext Boundaries**:
  - **Forbidden**: Master passwords, KEK, DEK, vault plaintext, credential passwords, authentication secrets, and recovery keys must **NEVER** be stored in `settings.json`.

### 3.8 Clipboard Manager (`app.services.clipboard`)
- **Responsibilities**:
  - Place requested credential text (username or password) into the system clipboard via Qt's `QClipboard`.
  - Launch an asynchronous countdown timer (default: 30 seconds).
  - Upon timer expiry, verify if the clipboard still contains the exact sensitive text; if so, clear it.
  - Provide immediate manual "Clear Clipboard Now" capability.
- **Boundaries**:
  - Does not log clipboard contents to disk or persist history.

---

## 4. Key Data Flows

### 4.1 Vault Unlock Sequence
```
[User] 
  │ enters Master Password
  ▼
[LoginView] 
  │ passes password to
  ▼
[AuthenticationLayer]
  │ queries StorageLayer for header (38B public header + wrapped DEK)
  ▼
[StorageLayer] ────► returns Public Header & Wrapped DEK Envelope
  │
  ▼
[AuthenticationLayer]
  │ passes (password, salt, KDF params) to
  ▼
[CryptographyLayer] ────► derives KEK via Argon2id
  │
  ▼
[CryptographyLayer] ────► attempts AES-256-GCM decrypt of Wrapped DEK using KEK & AAD_DEK
  │
  ├─► [Failure / Tag Mismatch] ──► raises AuthenticationError ──► [LoginView shows generic error]
  │
  └─► [Success] ──► returns DEK
        │
        ▼
[VaultManager]
  │ uses DEK to decrypt Vault Payload via CryptographyLayer with AAD_PAYLOAD
  ▼
[CryptographyLayer] ────► returns decrypted JSON payload bytes
  │
  ▼
[VaultManager] ────► deserializes JSON into Credential entities
  │
  ▼
[SessionManager] ────► marks state = UNLOCKED, starts 10-minute timer
  │
  ▼
[GUI Layer] ────► switches view to MainVaultView
```

### 4.2 Save Mutation Sequence
```
[User] ──► edits or adds credential in UI
  │
  ▼
[VaultManager] 
  │ updates in-memory list, serializes collection to JSON bytes
  ▼
[CryptographyLayer] 
  │ generates fresh 12-byte random Nonce
  │ constructs AAD_PAYLOAD (18 bytes: MAGIC + FORMAT_VERSION + PAYLOAD_LEN)
  │ encrypts payload bytes with DEK (AES-256-GCM)
  │ returns (Nonce, Tag, Ciphertext)
  ▼
[StorageLayer] 
  │ packs binary header (134 bytes) + encrypted payload
  │ writes to "vault.svault.tmp"
  │ executes os.fsync()
  │ executes os.replace("vault.svault.tmp", "vault.svault")
  ▼
[GUI Layer] ──► shows saved status indicator
```

### 4.3 Inactivity Auto-Lock Sequence
```
[SessionManager Inactivity Timer: 10 mins elapsed OR User clicks Lock Vault]
  │
  ▼
[SessionManager] ──► triggers lock()
  │
  ├─► [VaultManager] ──► clears decrypted records from memory
  ├─► [CryptographyLayer] ──► best-effort zeroing and dereferencing of DEK and KEK
  ├─► [ClipboardManager] ──► clears clipboard if active
  └─► [GUI Layer] ──► closes open dialogs, resets views, renders LoginView (LOCKED state)
```

---

## 5. Security Enclaves & Memory Hygiene

1. **Memory State**:
   - Master password bytes exist transiently during the KDF execution call, then references are immediately set to `None`.
   - The DEK exists in memory only while `SessionManager.state == UNLOCKED`.
   - On transition to `LOCKED` or application close, memory references are unlinked, and mutable byte buffers are zeroed on a best-effort basis.
2. **Disk Isolation**:
   - Plaintext credentials are never written to temporary files or swap on disk by application logic.
   - Logs never record decrypted records, passwords, or raw cryptographic keys.
