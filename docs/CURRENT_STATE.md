# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M0 — Architecture & Security Design`
- **Status**: **Ready to Freeze / Commit**
- **Target Release**: Version 1.0.0 (Windows)

---

## 2. Completed Work (Milestone 0)

- **Architecture Design**: Component boundaries defined between GUI, Authentication, Session, Vault, Cryptography, Storage, Settings, and Clipboard managers (`docs/ARCHITECTURE.md`).
- **Security Model**: Classified assets, trust boundaries, persistence rules, session lifecycle, and explicit limitations documented (`docs/SECURITY_MODEL.md`).
- **Cryptographic Design**: Argon2id KDF parameters (64 MiB RAM, 3 iterations, 4 parallelism, 16-byte salt) and AES-256-GCM AEAD encryption with two-tier KEK/DEK hierarchy and 12-byte CSPRNG nonces (`docs/CRYPTOGRAPHY.md`).
- **Vault Format Design**: Verified exact 134-byte fixed binary header layout (`0x00 - 0x85`), master-password-independent `AAD_PAYLOAD`, and JSON schema (`docs/DATA_FORMAT.md`).
- **Threat Model**: Categorized mitigated threats vs. host-level compromise realities outside scope (`docs/THREAT_MODEL.md`).
- **UI Design**: Detailed specifications for all 11 planned application screens, session states, and keyboard shortcuts (`docs/UI_DESIGN.md`).
- **Testing Strategy**: Defined test pyramid, cryptographic verification, tamper injection tests, headless Qt QA, and settings security bounds (`docs/TESTING.md`).
- **Development Roadmap**: 14-milestone roadmap structured from M0 to M14 (`docs/DEVELOPMENT_ROADMAP.md`).
- **M0 Consistency & Security Review**: Thorough cross-document consistency pass completed; eliminated overclaims; reconciled exact byte offsets, header sizes, and AAD definitions.

---

## 3. Current Task
M0 final documentation review completed.

---

## 4. Next Task
Freeze and commit M0, then begin M1 (Project Skeleton & Documentation System).

---

## 5. Known Issues / Explicit Limitations
- **Host Compromise Out of Scope**: Application cannot defend against active OS-level keyloggers, rootkits, or malware with process-inspection privileges.
- **Python Memory Erasure**: Low-level memory zeroing in Python is best-effort (`bytearray` overwrite); absolute physical RAM erasure cannot be guaranteed at the OS/hardware level.
- **No Recovery in v1**: If the master password is forgotten, data cannot be recovered (intentional design).

---

## 6. Important Decisions Summary
- **ADR-001**: Python 3.11+ as primary language with best-effort memory hygiene.
- **ADR-002**: PySide6 (Qt 6 for Python) for desktop GUI.
- **ADR-003**: 100% Offline architecture (zero telemetry, zero networking).
- **ADR-004**: Single encrypted flat file (`.svault`), No SQLite.
- **ADR-005**: Sensitive vault data encrypted at rest via AES-256-GCM.
- **ADR-006**: Reversible authenticated encryption for credentials; no SHA-256 for passwords.
- **ADR-007**: Argon2id KDF (64 MiB, t=3, p=4, 16B salt).
- **ADR-008**: AES-256-GCM AEAD with KEK / DEK envelope hierarchy. Decoupled AAD: `AAD_DEK` (38B) and `AAD_PAYLOAD` (18B) allowing instant password rotation without payload re-encryption.
- **ADR-009**: No recovery keys in Version 1.
- **ADR-010**: Windows primary target (`%LOCALAPPDATA%\SecureVault\`), Linux-compatible design.
