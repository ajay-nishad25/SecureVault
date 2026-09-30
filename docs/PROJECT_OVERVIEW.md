# SecureVault — Project Overview

## 1. Product Purpose

**SecureVault** is an open-source, completely offline desktop password manager designed for local-first credential management. It empowers users to store, organize, search, and generate strong credentials without relying on remote servers, proprietary cloud services, internet connectivity, or subscription tiers.

In an era of recurring cloud data breaches and vendor lock-in, SecureVault ensures that the user retains local cryptographic custody of their sensitive credentials on their personal computer.

---

## 2. Target Users

- **Privacy-Conscious Individuals**: Users seeking full local custody of their sensitive credentials without trusting third-party cloud infrastructure.
- **Developers & Systems Engineers**: Technical users who prioritize transparent security design, offline reliability, and open-source auditability.
- **Air-Gapped & High-Security Environments**: Workstations operating with restricted or zero network access where cloud-synchronized password managers cannot function or are prohibited by policy.
- **Everyday Desktop Users**: Users who desire a straightforward, responsive, clean desktop application to replace vulnerable spreadsheets, text files, or reused passwords.

---

## 3. Main Features (Core Capabilities)

1. **Local Encrypted Vault**: All credentials, notes, and metadata are encrypted in a dedicated local binary file (`vault.svault`) stored in user application data.
2. **Master Password Protection**: Access is gated by a single master password transformed into a cryptographic key using the modern Argon2id key derivation function.
3. **Authenticated Encryption**: Symmetrically encrypted with AES-256-GCM (Authenticated Encryption with Associated Data), preventing unauthorized decryption and detecting physical file tampering.
4. **Credential Management (CRUD)**:
   - Create, Read, Update, and Delete entries.
   - Fields: Title/Service, Username/Email, Password, Category, Tags, and Notes.
   - Timestamps: Created and last updated (ISO-8601 UTC).
5. **Instant Search & Filtering**: Fast in-memory filtering across account titles, usernames, categories, and tags.
6. **Password Generator**: Configurable generator supporting variable lengths, uppercase, lowercase, numbers, and symbols with cryptographic randomness.
7. **Session Security & Auto-Lock**: Automatic vault locking after 10 minutes of user inactivity, plus immediate manual lock capability (`Ctrl+L`).
8. **Secure Clipboard Assistance**: Quick copy buttons for username and password with an automatic clipboard clear timer (default: 30 seconds).
9. **Zero Network Activity**: No network calls, telemetry, analytics, update checks, or remote dependencies.

---

## 4. Version 1 (v1) Scope

| Area | In-Scope for v1 |
| :--- | :--- |
| **Platform** | Windows (Windows 10/11 64-bit). |
| **Language & Framework** | Python 3.11+ with PySide6 (Qt for Python). |
| **Storage Architecture** | Single encrypted binary file (`.svault`) using atomic file writes. No SQLite. |
| **Cryptography** | Argon2id KDF + AES-256-GCM authenticated encryption (Two-tier KEK/DEK hierarchy). |
| **Authentication** | Single master password. |
| **Session Control** | Inactivity timeout (10 min default), manual lock, best-effort memory clearing on lock. |
| **Data Fields** | Title/Account, Username/Email, Password, Notes. |
| **Utility** | Configurable password generator, 30s clipboard auto-clear. |
| **Packaging** | Standalone Windows executable/installer via PyInstaller. |

---

## 5. Explicitly Excluded Features (Out of Scope for v1)

The following capabilities are deliberately excluded from Version 1 to prevent architectural bloat and maintain a minimal attack surface:

- **CSV Export**: SecureVault deliberately does not provide unencrypted CSV export functionality.
- **Recovery Keys / Backdoors**: If the master password is lost, the vault cannot be recovered. No master keys, escrow systems, or backdoors exist.
- **SQLite Database**: Flat encrypted file envelope only; no relational database engine on disk.
- **Cloud Synchronization & Remote Storage**: No sync across Dropbox, Google Drive, OneDrive, WebDAV, or custom servers.
- **Browser Extension Integration**: No native messaging host or local HTTP/WebSocket listener.
- **Mobile Applications**: No iOS or Android clients.
- **Biometric Authentication**: No Windows Hello / Touch ID / FIDO2 integration in v1.
- **Multi-User / Shared Vaults**: Strictly single-user local vaults.
- **Hardware Security Modules (HSM) / Smartcards**: Pure software cryptographic foundation in v1.
- **Network / Telemetry / Crash Reporting**: Zero external outbound network sockets.

---

## 6. Future Features (Post-v1 / Roadmap Considerations)

- **Linux Portability**: Flatpak/AppImage packaging and Linux desktop integration.
- **Offline Password Health / Breach Detection**: Offline checks against known breached prefixes using k-anonymity bloom filters.
- **File Attachments**: Encrypted attachment storage within the vault format.
- **Passkey / FIDO2 Credential Storage**: Support for WebAuthn/FIDO2 credentials.
- **Hardware Key Unlock (YubiKey / FIDO2)**: Optional two-factor or hardware-backed unlock mechanism.
- **Portable Mode**: Standalone executable and vault on a removable USB flash drive.
