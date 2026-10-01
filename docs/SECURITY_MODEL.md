# SecureVault — Security Model

## 1. Security Philosophy

SecureVault is built around a **Local-First, Zero-Knowledge, Defense-in-Depth** security philosophy. The security of the stored vault relies on established mathematical cryptography (Argon2id password key derivation and AES-256-GCM authenticated encryption) rather than obscurity.

We adhere strictly to Kerckhoffs's principle: **the system remains secure even if everything about its implementation is public knowledge, so long as the user's master password remains secret and has adequate entropy.**

---

## 2. Assets & Data Classification

| Classification | Assets | Location | Protection Mechanism |
| :--- | :--- | :--- | :--- |
| **Critical Secrets** | Master Password | Ephemeral memory only | Never written to disk; discarded immediately after KDF. |
| **Critical Keys** | Derived KEK, Vault DEK | Session memory only | Ephemeral in-memory buffers; purged on session lock. |
| **Protected Data** | Account titles, usernames, passwords, notes, tags | Local disk / Session memory | Encrypted with AES-256-GCM at rest; loaded only while unlocked. |
| **Vault Metadata** | Salt, KDF parameters, format version, nonces, tags | Local disk (`vault.svault`) | Stored in plaintext header, authenticated via AEAD. |
| **Non-Sensitive Preferences** | UI theme, window size, auto-lock timeout | Local disk (`settings.json`) | Plaintext JSON in local application data. |

---

## 3. Trust Boundaries

```
+-------------------------------------------------------------------------+
| UNTRUSTED ENVIRONMENT                                                   |
| - External Network & Internet (Completely blocked/omitted)             |
| - Unauthorized Persons with Physical Access (Protected by Master Key)  |
| - Cloud Storage / Removable Drives carrying .svault file                |
+-------------------------------------------------------------------------+
                                    |
                                    v [Master Password Barrier]
+-------------------------------------------------------------------------+
| TRUSTED COMPUTING BASE (TCB)                                            |
| - Operating System Kernel & Hardware (Assumed uncompromised)            |
| - Python Runtime & Verified Dependencies (cryptography, PySide6)        |
| - SecureVault Application Process Memory (Active Session)               |
+-------------------------------------------------------------------------+
```

### 3.1 What is Trusted
- **The Host Operating System**: The underlying Windows OS (and future Linux kernel) is assumed to provide standard process memory isolation, non-tampered page file management, and a cryptographically secure random number generator (OS CSPRNG).
- **Python Standard Library & Verified Dependencies**: The core Python interpreter, `cryptography` (OpenSSL backend), and `argon2-cffi` are trusted to execute cryptographic instructions correctly without side-channel leaks within their control.
- **The User**: The authorized user is trusted to choose a strong, non-guessable master password and to keep their computer physically secured when unattended.

### 3.2 What is Untrusted
- **Persistent Storage at Rest**: The file system where `vault.svault` resides is treated as potentially readable and modifiable by unauthorized parties (e.g. copied via USB, shared drive, or backup theft).
- **The Network**: The network is completely untrusted. To eliminate remote attack vectors, SecureVault includes **no networking code**, does not listen on any local sockets, and initiates zero outbound requests.
- **Third-Party Processes on the Host**: Other non-administrative software running on the user's system should not be granted access to the vault file or application memory.

---

## 4. Storage & Persistence Inventory

### 4.1 What is Stored Locally
1. **The Vault File (`%LOCALAPPDATA%\SecureVault\vault.svault`)**:
   - File format magic bytes and format version identifier.
   - Cryptographic salt (16 bytes random).
   - Argon2id parameters (memory cost, iteration count, parallelism lanes).
   - Wrapped DEK envelope (12-byte nonce, 32-byte ciphertext, 16-byte auth tag).
   - Encrypted Vault Payload (8-byte length, 12-byte payload nonce, 16-byte auth tag, ciphertext).
2. **User Preferences (`%LOCALAPPDATA%\SecureVault\settings.json`)**:
   - **Allowed Fields (Non-Sensitive Only)**:
     - `theme`: `"system"`, `"dark"`, or `"light"`
     - `auto_lock_minutes`: Integer (1 to 60, default 10)
     - `clipboard_clear_seconds`: Integer (10 to 120, default 30)
     - `window_width` / `window_height`: Integers

### 4.2 What is NEVER Stored in `settings.json` or Plaintext Files
- **Master Password**: Never stored in any form.
- **Key Encryption Key (KEK)**: Never stored.
- **Data Encryption Key (DEK)**: Never stored unencrypted.
- **Vault Plaintext / Credentials / Notes**: Never stored in settings or unencrypted files.
- **Authentication Secrets / Tokens / Recovery Phrases**: Never stored.

---

## 5. Authentication Flow

```
1. User enters Master Password in LoginView.
2. Application reads vault header (38 bytes) from disk: salt and Argon2id parameters.
3. Argon2id derives 256-bit Key Encryption Key (KEK).
4. Cryptography layer attempts AES-256-GCM decryption of the Wrapped DEK using KEK and AAD_DEK:
   - If tag validation succeeds: DEK is unwrapped into session memory.
   - If tag validation fails: Cryptographic error is caught, and a generic 
     "Invalid master password or corrupted vault" notification is returned.
5. DEK decrypts the Vault Payload ciphertext using AAD_PAYLOAD:
   - If tag validation succeeds: JSON bytes are parsed and loaded into memory.
   - If tag validation fails: Generic corruption/tamper error returned.
6. Transient master password byte buffers are discarded immediately.
```

---

## 6. Session Lifecycle & State Transitions

The application manages three distinct session states:
- `UNINITIALIZED`: No vault file exists; first-run wizard is active.
- `LOCKED`: Vault file exists on disk, but no keys or decrypted credentials exist in memory. `LoginView` is displayed.
- `UNLOCKED`: Master password authenticated, DEK active in memory, decrypted credentials accessible.

```
       [Launch App (no vault)] ──► UNINITIALIZED ──► [Setup Complete] ──┐
                                                                         │
┌─────────────────────────────── LOCKED ◄───────────────────────────────┘
│                                  │
│                                  │ (Successful Master Password Auth)
│                                  ▼
│                               UNLOCKED
│                                  │
│   ├── Inactivity (10 min) ───────┤
│   ├── Manual Lock (Ctrl+L) ──────┤
│   └── App Close / OS Sleep ──────┤
│                                  │
└──────────────────────────────────┘
```

### Locking Behavior:
When transitioning from **UNLOCKED** to **LOCKED** (via timeout, `Ctrl+L`, or closing the application):
1. All decrypted credential objects are cleared from memory references.
2. Mutable key byte buffers (`DEK`, `KEK`) are overwritten with zeros on a best-effort basis and dereferenced.
3. The system clipboard is cleared if it contains credential text copied from SecureVault.
4. Active GUI dialogs and forms are closed, and the interface resets to `LoginView`.
5. Reopening the application or returning to the locked window strictly requires re-entering the master password.

---

## 7. Security Guarantees vs. Explicit Limitations

### 7.1 What SecureVault IS Designed to Protect Against
- **Theft of the Vault File (`vault.svault`)**: Offline dictionary/brute-force attacks are constrained by Argon2id memory-hardness (64 MiB RAM per attempt).
- **Physical Vault File Tampering**: Any bit-flipping, header parameter tampering, or file truncation triggers immediate AEAD authentication tag failure, preventing corrupted data ingestion.
- **Unauthorized Access to Locked Workstations**: When the application is locked, no decrypted credentials remain accessible in the user interface.
- **Unattended Workstation Inactivity**: Automatic lock after 10 minutes of idle time mitigates shoulder surfing or walk-up access.
- **Transient Clipboard Snooping**: Sensitive passwords copied to the clipboard are cleared automatically after 30 seconds.
- **Write Interruption / Power Outage**: Atomic file replacement (`os.replace`) prevents vault file corruption during crashes.

### 7.2 What SecureVault DOES NOT Protect Against (Explicit Limitations)
1. **Compromised Operating System / Active Malware**: If the host OS has active malware running with user or administrative privileges (e.g., keyloggers, screen scrapers, API hooks, or malicious memory scanners), keystrokes can be captured as the master password is typed, and process memory can be inspected. No user-space software can defend against a compromised host.
2. **Guaranteed Physical Memory Erasure**: Python's runtime memory allocator (`pymalloc`), immutable strings, and garbage collection do not provide operating-system-level guarantees that deallocated memory pages are immediately wiped from physical RAM. While SecureVault performs best-effort zeroing on mutable `bytearray` buffers, residual byte fragments may persist in unallocated process memory, OS page files, or hibernation dumps.
3. **Privileged Clipboard Monitoring Tools**: Third-party software running concurrently with clipboard monitoring privileges can intercept copied passwords before the 30-second clear timer fires.
4. **Physical Access to an Already-Unlocked Session**: If an attacker accesses the machine while the vault is actively unlocked and before the inactivity timer expires, they can view credentials.
5. **Lost Master Passwords**: Because there are **no recovery keys**, **no backdoors**, and **no cloud reset** in Version 1, a forgotten master password results in permanent loss of access.

---

### 7.3 Clipboard Security Architecture (Milestone M10)
- **Supported Fields**: Usernames / Login IDs and Passwords can be explicitly copied via UI buttons (`[ Copy Username ]`, `[ Copy Password ]`).
- **30-Second Auto-Clear Watchdog**: Every SecureVault copy arms an automatic 30-second countdown timer (`CLIPBOARD_CLEAR_TIMEOUT_SECONDS = 30`).
- **Strict Ownership Verification**: Before clearing, `ClipboardService` compares the current OS clipboard text against the exact value SecureVault placed. It clears the clipboard if and only if the exact SecureVault value is still present.
- **Protection of User Data**: If the user or another application replaces the clipboard during the 30-second window, SecureVault skips clearing, leaving external content completely untouched.
- **Overlapping Copy Management**: Copying a new value immediately disarms previous timers and establishes ownership over the latest value.
- **Session Lock & Shutdown**: Transitioning to `LOCKED` or closing the application triggers immediate `clear_if_owned()`.
- **Zero Passive Monitoring**: SecureVault does NOT continuously monitor the OS clipboard, does NOT record clipboard history, does NOT persist clipboard data to disk or logs, and maintains no background polling.

---

### 7.4 Security Hardening Architecture (Milestone M11)
- **Deterministic Ephemeral Buffer Hygiene (`SEC-M11-01`, `SEC-M11-02`)**:
  - Key Encryption Keys (KEK) are ingested and held strictly in mutable `bytearray` containers.
  - `zero_buffer()` execution is guaranteed inside `finally` blocks immediately upon completion or failure of DEK wrapping/unwrapping operations in `create_vault()`, `unlock_vault()`, and `change_master_password()`.
  - Immutable `bytes(kek)` conversion is restricted to the exact point of invocation into cryptography's `AESGCM`.
  - Transient master password UTF-8 representations are converted to mutable `bytearray` buffers in `derive_kek()` and explicitly wiped with `zero_buffer()` in `finally`.
  - Realistic memory model boundary: While mutable `bytearray` buffers are deterministically cleared in-place via `ctypes.memset` / slice zeroing, Python high-level `str` instances are immutable and subject to interpreter lifecycle and garbage collection.
- **In-Memory Save Atomicity (`SEC-M11-03`)**:
  - `save_vault()` constructs staged copies of payload metadata (`updated_at`) and header structures separately from the active vault object.
  - In-memory state mutation is committed strictly *after* atomic disk persistence (`write_vault_file()`) completes without error.
  - If disk I/O, encryption, or file system operations fail, the in-memory vault session remains completely untouched, preventing synchronization drift.
- **Constant-Time Rotation Checks (`SEC-M11-04`)**:
  - Password rotation verification utilizes `hmac.compare_digest()` to compare current and prospective master passwords, mitigating timing side channels. Identical submissions trigger `PasswordReuseError`.
