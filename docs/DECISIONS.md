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
