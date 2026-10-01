# SecureVault — Architecture Decision Records (ADRs)

This document records the foundational architectural decisions governing SecureVault.
Each record details the context, decision, and consequences.

---

## ADR-001: Python as Primary Language
- **Status**: Accepted
- **Context**: Need a cross-platform language with robust cryptography bindings, strong GUI ecosystems, active security maintenance, and rapid development capabilities.
- **Decision**: Python 3.11+ is selected as the primary programming language.
- **Consequences**:
  - *Positive*: Rich standard library (`secrets`, `json`, `pathlib`), industry-standard C-bindings for cryptography (`cryptography`, `argon2-cffi`), and excellent developer ergonomics.
  - *Trade-off*: Dynamic memory management and Python object immutability mean that low-level memory zeroing cannot be guaranteed at the OS/hardware level. Memory hygiene measures (overwriting mutable `bytearray` buffers and unlinking references) are best-effort.

---

## ADR-002: PySide6 as GUI Framework
- **Status**: Accepted
- **Context**: Need a desktop UI framework providing native look-and-feel, robust event filters, high-DPI scaling, and solid cross-platform support for Windows and Linux.
- **Decision**: PySide6 (official Qt 6 bindings for Python) is chosen as the desktop GUI toolkit.
- **Consequences**:
  - *Positive*: Mature widget set, powerful event filtering for session idle detection, built-in clipboard management (`QClipboard`), native OS integration, and modern styling via Qt Style Sheets (QSS).
  - *Trade-off*: Increases binary distribution size compared to minimal web-views or Tkinter; mitigated through PyInstaller optimization in M13.

---

## ADR-003: Completely Offline Architecture
- **Status**: Accepted
- **Context**: Cloud password managers represent high-value remote targets subject to breaches, outages, and subpoena risks.
- **Decision**: SecureVault is completely offline. It contains no networking code, no telemetry, no analytics, no remote database synchronization, and no background update checks.
- **Consequences**:
  - *Positive*: Attack surface is drastically minimized; eliminates remote network exploit vectors; builds total trust with privacy-conscious users.
  - *Trade-off*: Multi-device synchronization must be handled manually by the user (e.g. moving the `.svault` file via secure media).

---

## ADR-004: No SQLite Database
- **Status**: Accepted
- **Context**: Traditional password managers often embed relational databases like SQLite. However, SQLite writes temporary rollbacks, journals, write-ahead logs (WAL), and unencrypted page caches to disk, which can leak unencrypted data fragments.
- **Decision**: SecureVault will NOT use SQLite. The vault is stored as a single encrypted flat binary file (`.svault`).
- **Consequences**:
  - *Positive*: Deterministic control over data persisted to disk; no journal or WAL leakage; zero database engine dependencies; atomic replacement via `os.replace`.
  - *Trade-off*: In-memory querying requires loading all entries at unlock time. Because desktop password vaults typically contain under 10,000 items (under 5 MB JSON), in-memory filtering is instantaneous (< 10ms).

---

## ADR-005: Sensitive Vault Data is Encrypted at Rest
- **Status**: Accepted
- **Context**: Passwords, usernames, security notes, and metadata must never be readable if the storage drive or file is inspected at rest.
- **Decision**: All credential attributes (titles, usernames, passwords, notes, tags) are encrypted using AES-256-GCM before writing to disk.
- **Consequences**:
  - *Positive*: Strong confidentiality against passive disk theft, lost laptops, or backup exposure.
  - *Trade-off*: Disk reads and writes require cryptographic processing; completely imperceptible on modern CPUs.

---

## ADR-006: No SHA-256 for Storing Recoverable Passwords
- **Status**: Accepted
- **Context**: Users must be able to view, edit, and copy their saved passwords. One-way hash algorithms (like SHA-256) are mathematically irreversible and unsuitable for credential storage.
- **Decision**: Passwords must be protected using authenticated symmetric encryption, not one-way hashing. One-way KDFs (Argon2id) are reserved exclusively for deriving encryption keys from the user's master password.
- **Consequences**:
  - *Positive*: Retains recoverable plaintext credentials inside the unlocked session while maintaining authenticated encryption at rest.
  - *Trade-off*: Requires rigorous key management and session lifecycle boundaries to protect the decryption key in memory.

---

## ADR-007: Argon2id as Password Key Derivation Function (KDF)
- **Status**: Accepted
- **Context**: A human master password does not possess uniform 256-bit cryptographic entropy. Fast hashes (SHA-256, MD5) can be brute-forced at billions of guesses per second on modern GPUs.
- **Decision**: SecureVault utilizes Argon2id (RFC 9106) with parameters: 64 MiB memory (`65536 KiB`), 3 iterations, 4 parallelism lanes, and 16 bytes of CSPRNG salt.
- **Consequences**:
  - *Positive*: Hybrid resistance against both GPU-accelerated brute forcing (memory hardness) and side-channel cache attacks.
  - *Trade-off*: Master password unlock introduces an intentional ~0.3 to 0.6 second calculation delay on modern desktop CPUs.

---

## ADR-008: Authenticated Encryption with Two-Tier Key Hierarchy (KEK / DEK)
- **Status**: Accepted
- **Context**: Encrypting large files directly with a password-derived key requires re-encrypting the entire database whenever the master password changes. Furthermore, unauthenticated encryption modes (like CBC without HMAC) are vulnerable to bit-flipping and padding oracles.
- **Decision**: SecureVault adopts **AES-256-GCM** (AEAD) using a two-tier key hierarchy:
  1. A random 256-bit Data Encryption Key (DEK) encrypts the vault payload with `AAD_PAYLOAD` (`MAGIC` + `FORMAT_VERSION` + `PAYLOAD_LEN`, 18 bytes).
  2. The Master Password derives a 256-bit Key Encryption Key (KEK) via Argon2id, which wraps (encrypts) the DEK with `AAD_DEK` (first 38 bytes of public header).
- **Consequences**:
  - *Positive*: Changing master passwords only requires re-wrapping the 32-byte DEK (instantaneous and atomic). Because `AAD_PAYLOAD` excludes salt and KEK parameters, the payload ciphertext and auth tag remain valid without re-encryption. AES-256-GCM guarantees tamper detection via 128-bit authentication tags.
  - *Trade-off*: Requires a structured 134-byte fixed binary envelope.

---

## ADR-009: Recovery Keys Excluded from Version 1
- **Status**: Accepted
- **Context**: Recovery mechanisms introduce complexity, potential backdoors, social engineering vulnerabilities, and user confusion if not implemented with flawless key escrow or Shamir's Secret Sharing.
- **Decision**: Version 1 will NOT include recovery keys or emergency contacts. If the master password is lost, the vault cannot be unlocked.
- **Consequences**:
  - *Positive*: Zero backdoors, zero escrow risks, simple and uncompromising security model.
  - *Trade-off*: User bears full responsibility for remembering their master password; mandatory warnings must be confirmed during setup.

---

## ADR-010: Windows First, Portable to Linux
- **Status**: Accepted
- **Context**: Target users are predominantly Windows desktop users initially, with Linux workstations as the planned secondary platform.
- **Decision**: Windows 10/11 64-bit is the tier-1 target. All file paths (`%LOCALAPPDATA%\SecureVault\`), OS interactions, and packaging adhere to standard POSIX-compatible Python patterns to ensure clean portability to Linux in future milestones.
- **Consequences**:
  - *Positive*: High initial quality by focusing on Windows `%LOCALAPPDATA%` and Windows packaging first, without introducing platform-specific abstractions that break on Linux.
  - *Trade-off*: Linux-specific keyring integration is deferred to post-v1.

---

## ADR-011: Safe Configuration & Logging Boundaries
- **Status**: Accepted (Milestone M1)
- **Context**: Desktop applications often inadvertently serialize runtime secrets into config files or emit them into log files during debugging or error handling.
- **Decision**:
  1. Configuration is strictly restricted to non-sensitive operational parameters. Storing master passwords, KEK, DEK, vault plaintext, or recovery keys in configuration files is programmatically prohibited.
  2. The application logger installs a `SafeLogFilter` that actively redacts patterns matching passwords, tokens, keys, and secrets.
  3. No remote logging, cloud telemetry, or external log collectors are permitted.
- **Consequences**:
  - *Positive*: Eliminates accidental credential exposure in config files (`settings.json`) or terminal logs.
  - *Trade-off*: Developers must inspect redacted values in debuggers rather than dumping raw credential strings to console logs.

---

## ADR-012: Zero-Verifier / KEK-Only Master Authentication
- **Status**: Accepted (Milestone M3)
- **Context**: Traditional web and desktop applications often authenticate users by comparing the hash of an entered password against a stored password hash or authentication verifier file (e.g., `auth.json`, `password_hash.txt`, or shadow file). In an encrypted local vault architecture, storing a dedicated password verifier on disk introduces significant security risks:
  1. An adversary who gains local disk access can launch high-speed offline dictionary or brute-force attacks directly against the stored verifier without attempting cryptographic vault decryption.
  2. Verifier databases create an unnecessary persistent target and risk desynchronization between the "authentication" password and the "vault encryption" key.
- **Decision**:
  1. SecureVault strictly adheres to a **Zero-Verifier Architecture**. No password hash, salt-hash pair, password verifier, or persistent authentication credential file is ever written to disk.
  2. Master authentication is established purely through cryptographic key derivation:
     ```text
     Master Password + Salt -> Argon2id -> 32-byte KEK
     ```
  3. In M3, authentication success is verified by the mathematical derivation of the 32-byte KEK from valid inputs.
  4. In M4 and beyond, authentication validity is verified implicitly and solely by attempting to unwrap (AES-256-GCM decrypt) the Data Encryption Key (DEK) from the vault file header. If the master password is incorrect, the derived KEK differs and AES-GCM authentication tag verification fails, returning an indistinguishable error.
- **Consequences**:
  - *Positive*: An attacker with access to the vault file has only the ciphertext and wrapped DEK to target; there is zero separate verifier artifact to attack. Eliminates credential desynchronization.
  - *Trade-off*: Authentication cannot be verified without performing the full Argon2id key derivation and attempting cryptographic unwrapping against the vault header.

---

## ADR-013: Decoupled AAD Envelope Architecture for Atomic Key Rotation
- **Status**: Accepted (Milestone M4)
- **Context**: In an envelope-encrypted database, rotating the master password requires deriving a new Key Encryption Key (KEK) with a fresh salt and re-wrapping the Data Encryption Key (DEK). If the Associated Authenticated Data (AAD) for the payload ciphertext included the salt, KDF parameters, or wrapped DEK, changing the master password would invalidate the payload authentication tag, forcing re-encryption of the entire database.
- **Decision**:
  1. `AAD_DEK` (38 bytes) binds the public header (`MAGIC` + `FORMAT_VERSION` + `KDF_ID` + `KDF_MEMORY` + `KDF_TIME` + `KDF_PARALLEL` + `SALT_LEN` + `SALT`). Any tampering with KDF parameters or salt causes DEK unwrapping to fail.
  2. `AAD_PAYLOAD` (18 bytes) binds only the immutable envelope prefix and length (`MAGIC` [8B] + `FORMAT_VERSION` [2B] + `PAYLOAD_LEN` [8B]).
  3. `AAD_PAYLOAD` strictly excludes KDF parameters, salt, DEK nonce, wrapped DEK, and DEK tag.
- **Consequences**:
  - *Positive*: Master password rotation is atomic, instantaneous, and risk-free. Only the 134-byte file header is rewritten with the new salt and re-wrapped DEK; the large encrypted payload ciphertext is not touched or re-encrypted.
  - *Positive*: Full cryptographic tamper detection is maintained for both key wrapping and payload bounds.
  - *Trade-off*: Slicing non-contiguous byte ranges requires explicit offsets (`0x00:0x0A` and `0x62:0x6A`) during AAD assembly.

---

## ADR-014: In-Memory Credential CRUD & Immediate Atomic Vault Re-Encryption
- **Status**: Accepted (Milestone M5)
- **Context**: In Milestone M5, SecureVault establishes the credential data layer. When credentials are created, updated, or deleted in an active unlocked vault session, the modifications must be persisted safely and reliably without creating unencrypted intermediate artifacts, corrupting existing key material, or desynchronizing in-memory and on-disk states.
- **Decision**:
  1. **Strict Credential Model**: An individual credential consists of exactly `id`, `title`, `username`, `password`, and `notes`. No `type` or category fields are included in M5.
  2. **Automated Identity**: `id` is an automatically generated UUID string, ensuring vault-wide uniqueness.
  3. **Immediate Atomic Re-Encryption**: Every mutating CRUD operation (`create_credential`, `update_credential`, `delete_credential`) delegates directly to `VaultService.save_vault()`. The in-memory JSON payload is serialized, re-encrypted under the active in-memory DEK with a fresh 12-byte CSPRNG nonce and 18-byte `AAD_PAYLOAD`, and atomically persisted using a `.tmp` file and atomic replace.
  4. **Frozen Header Preservation**: The public header, KDF parameters, salt, and wrapped DEK are preserved byte-for-byte; only the payload length, nonce, and authentication tag are updated in the 134-byte header.
  5. **Representation Masking**: `Credential.__repr__` automatically redacts secret passwords to `'***'` to prevent inadvertent disclosure in debug output, logs, or exceptions.
  6. **Plaintext Export Exclusion**: SecureVault explicitly rejects unencrypted plaintext CSV export to protect user data from accidental unencrypted exposure.
- **Consequences**:
  - *Positive*: Crash resilience; mutations are immediately committed to disk under authenticated encryption.
  - *Positive*: Reuses vetted M4 AES-256-GCM primitives without cryptographic duplication.
  - *Positive*: In-memory representation remains synchronized with persistent `.svault` storage.

---

## ADR-015: Event-Driven Inactivity Monitoring & Two-Stage Auto-Lock Lifecycle
- **Status**: Accepted (Milestone M7)
- **Context**: In Milestone M7, SecureVault requires automated session protection to secure active unlocked vaults against unattended physical access. The system must reliably detect user inactivity, alert the user with a countdown without visual distraction during active work, avoid false resets, and automatically lock the vault without inventing duplicate cryptographic or thread-based locking mechanisms.
- **Decision**:
  1. **Two-Stage Timing Model**: Total inactivity timeout is fixed at 2 minutes 15 seconds (135 seconds), divided into:
     - 15-second hidden grace period: Countdown is completely hidden.
     - 2-minute visible countdown: Displays `Auto-lock: 02:00` decrementing once per second to `00:00`.
  2. **Strict Activity Whitelist**: Activity detection is handled centrally via `ActivityEventFilter` on the `QApplication` instance, capturing `KeyPress` (typing), `MouseButtonPress` (clicking), and `Wheel` (scrolling).
  3. **Mouse Movement Exclusion**: Mouse movement alone (`MouseMove`) is strictly excluded from resetting inactivity to prevent unintended resets from ambient pointer drift or bumping.
  4. **Single-Cell Overlay UI Alignment**: The top-right countdown label is positioned within a single-cell `QGridLayout` overlay on the header row rather than an inline hbox with fixed spacers, ensuring the "🔓 SecureVault — Unlocked" header remains centered across the entire window width regardless of timer visibility.
  5. **Unified Lock Path**: Inactivity timeout (`00:00`) dispatches through the existing `VaultService.lock_vault()` workflow, zeroing the active in-memory DEK, dismissing any open modal dialogs, and returning to `LockedView`.
  6. **Zero Secret Storage**: `SessionManager` stores only timing counters and state enums; no master passwords, KEKs, DEKs, or credentials are ever stored or referenced.
  7. **No Background Worker Threads for Timers**: Timing is managed entirely via Qt's native event-loop `QTimer` primitives (`grace_timer` and `countdown_timer`), preventing thread-synchronization race conditions and deadlocks.
- **Consequences**:
  - *Positive*: Robust, leak-free session security with zero CPU overhead when idle.
  - *Positive*: Header alignment remains pixel-perfect across all timer states.
  - *Positive*: Single cryptographic lock mechanism avoids duplicate security maintenance.
  - *Trade-off*: Event filter must be properly uninstalled on lock or view teardown to avoid Qt use-after-free conditions.

---

## ADR-016: Non-Sensitive Preferences Architecture, Centralized Dynamic Theming, and Cryptographic Master Password Rotation
- **Status**: Accepted (Milestone M8)
- **Context**: Milestone M8 completes preferences infrastructure, dynamic theme switching (Dark/Light), auto-lock duration customization (2, 5, 10, 15 minutes), and master password rotation. The system must strictly enforce that settings.json never stores secrets, auto-lock grace periods remain system-defined, theme changes take effect immediately without restart, and master password change operates cryptographically by re-wrapping the existing Data Encryption Key (DEK) atomically rather than re-encrypting all stored credentials.
- **Decision**:
  1. **Strictly Non-Sensitive Settings (`settings.json`)**:
     - `AppSettings` contains only `theme` ("dark" | "light") and `auto_lock_timeout` (120, 300, 600, 900 seconds).
     - Prohibited key list (`PROHIBITED_CONFIG_KEYS`) enforces an uncompromisable boundary: keys like `password`, `hash`, `kek`, `dek`, `salt`, `verifier`, `credentials`, `secret`, `token` raise an immediate `ConfigurationError`.
     - Atomic disk persistence is guaranteed via `.tmp` file and `os.replace`.
  2. **System-Defined 15-Second Grace Period**:
     - The 15-second inactivity grace period (`ACTIVITY_GRACE_SECONDS = 15`) remains strictly hardcoded and is not stored or editable in settings.
     - Changing the auto-lock setting adjusts only the subsequent countdown duration (2m / 5m / 10m / 15m) and updates the live `SessionManager` in real time.
  3. **Centralized Dynamic Theme Management (`ThemeManager`)**:
     - `ThemeManager` manages application-wide styling through curated `DARK_THEME_QSS` and `LIGHT_THEME_QSS` stylesheets applied directly to `QApplication`.
     - Switching between Dark and Light mode occurs instantly at runtime without application restart.
     - The saved theme preference is loaded and applied before any top-level window is rendered to prevent visual flash.
  4. **Cryptographic Master Password Rotation via DEK Re-Wrapping**:
     - When changing the master password, the user authenticates with their current master password.
     - The existing DEK is unwrapped in memory; a fresh 16-byte random salt is generated.
     - A new KEK is derived from the new password using Argon2id with existing production parameters.
     - The SAME existing DEK is re-wrapped with AES-256-GCM under the new KEK with a fresh 12-byte CSPRNG nonce and updated `AAD_DEK`.
     - The existing encrypted vault payload ciphertext, payload nonce, payload tag, and vault ID remain unchanged.
     - The new header is written atomically with the existing payload ciphertext via temporary file and replace.
     - Temporary KEK and DEK buffers are immediately zeroed using `zero_buffer`.
     - Upon completion, the vault session is immediately locked and the user is returned to `LockedView` where only the new password will unlock the vault.
- **Consequences**:
  - *Positive*: Zero risk of sensitive credential data corruption or plaintext leakage during password rotation.
  - *Positive*: Re-wrapping the DEK is instantaneous (constant time O(1)), regardless of vault size or credential count.
  - *Positive*: Seamless runtime theme switching with zero widget-scattered styling logic.
  - *Positive*: Settings persistence is completely safe and auditable.
