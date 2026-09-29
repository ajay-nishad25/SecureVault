# SecureVault

**SecureVault** is an open-source, completely offline desktop password manager built with Python and PySide6. It is designed for users who demand absolute privacy, zero-cloud architecture, and robust local cryptographic security.

---

## Key Principles

- **100% Offline & Zero-Cloud**: No internet connectivity, no remote servers, no account synchronization, and zero telemetry.
- **Modern Cryptography**: Powered by **Argon2id** (RFC 9106) for password-based key derivation and **AES-256-GCM** (NIST SP 800-38D) for authenticated encryption.
- **Flat Encrypted Storage**: Zero SQLite database dependencies. The entire vault is persisted in an encrypted binary envelope (`vault.svault`) with atomic write guarantees.
- **Two-Tier Key Hierarchy**: Master Password derives a Key Encryption Key (KEK) that wraps a uniformly random Data Encryption Key (DEK). Re-wrapping the DEK allows instant password rotation without re-encrypting the vault payload.
- **Session Security**: 10-minute inactivity auto-lock, immediate manual lock (`Ctrl+L`), and best-effort memory clearing on lock.
- **Zero-Backdoor Security**: No recovery keys or emergency bypasses in Version 1.

---

## Technical Stack

- **Language**: Python 3.11+
- **GUI Toolkit**: PySide6 (Qt 6 for Python)
- **Cryptographic Libraries**: `cryptography`, `argon2-cffi`
- **Initial Platform**: Windows 10/11 (with cross-platform architecture targeting Linux in post-v1)

---

## Project Status

- **Current Milestone**: `M0 — Architecture & Security Design` (Ready to Freeze / Commit)
- **Current Phase**: Architectural, cryptographic, and security specifications complete and verified. Implementation begins in `M1`.

---

## Documentation Index

Comprehensive project documentation is maintained in the [`docs/`](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/) directory:

- [AI Context & Handoff Guide](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/AI_CONTEXT.md)
- [Current Project State](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md)
- [Project Overview](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/PROJECT_OVERVIEW.md)
- [System Architecture](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/ARCHITECTURE.md)
- [Security Model](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/SECURITY_MODEL.md)
- [Cryptographic Architecture](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CRYPTOGRAPHY.md)
- [Vault Data Format Specification](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DATA_FORMAT.md)
- [UI/UX Design Specification](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/UI_DESIGN.md)
- [Threat Model](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/THREAT_MODEL.md)
- [Testing Strategy & QA](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/TESTING.md)
- [Development Roadmap](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DEVELOPMENT_ROADMAP.md)
- [Architecture Decision Records (ADRs)](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DECISIONS.md)

---

## License

Open Source — Planned under MIT or Apache 2.0 license upon v1.0.0 release.
