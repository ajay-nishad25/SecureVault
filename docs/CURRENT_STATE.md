# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M1 — Project Skeleton & Development Foundation`
- **Status**: **Implementation Complete / Ready for Review**
- **Target Release**: Version 1.0.0 (Windows)

---

## 2. Completed Work

### Milestone 0 (M0 — Architecture & Security Design)
- **Architecture Design**: Defined component boundaries across GUI, Auth, Session, Vault, Crypto, Storage, Settings, and Clipboard managers (`docs/ARCHITECTURE.md`).
- **Security Model**: Documented trust boundaries, assets, persistence inventory, session lifecycle, and explicit limitations (`docs/SECURITY_MODEL.md`).
- **Cryptographic Design**: Defined Argon2id KDF parameters and AES-256-GCM AEAD encryption with two-tier KEK/DEK hierarchy (`docs/CRYPTOGRAPHY.md`).
- **Vault Format Design**: Designed verified 134-byte fixed binary envelope and master-password-independent AAD (`docs/DATA_FORMAT.md`).
- **Threat Model**: Documented STRIDE-based threat matrix separating mitigated threats from host-level realities (`docs/THREAT_MODEL.md`).
- **UI Design**: Detailed 11-screen user flow, keyboard shortcuts, and session states (`docs/UI_DESIGN.md`).
- **Testing Strategy**: Defined test pyramid and verification criteria (`docs/TESTING.md`).
- **Development Roadmap**: Established M0 through M14 roadmap (`docs/DEVELOPMENT_ROADMAP.md`).
- **Architecture Decisions**: Documented ADR-001 through ADR-010 (`docs/DECISIONS.md`).

### Milestone 1 (M1 — Project Skeleton & Development Foundation)
- **Python Project Environment**: Established local virtual environment (`.venv/`) on Python 3.11.4; verified non-committed git status.
- **Dependency Management**: Established clear separation with `requirements.txt` (runtime: `PySide6>=6.5.0`), `requirements-dev.txt` (dev/test: `pytest>=7.4.0`), and standardized `pyproject.toml`.
- **Package Structure**: Scaffolded clean architecture packages matching M0 boundaries (`app/core/`, `app/crypto/`, `app/storage/`, `app/services/`, `app/models/`, `app/ui/`).
- **Application Entry Point**: Built minimal, clean startup/shutdown lifecycle in `main.py` with CLI flags (`--version`, `--check-config`).
- **Configuration Foundation**: Built `AppConfig` in `app.core.config` resolving Windows `%LOCALAPPDATA%\SecureVault\` with strict enforcement prohibiting sensitive secrets from settings.
- **Logging Foundation**: Built safe logging utility in `app.core.logging` featuring `SafeLogFilter` for automatic redaction of secret patterns in log messages.
- **Error Handling Foundation**: Built application domain exception hierarchy in `app.core.exceptions` (`SecureVaultError`, `ConfigurationError`, `StorageError`, `SecurityError`, `ValidationError`).
- **Test Infrastructure**: Built `pytest` suite in `tests/` with 27 passing unit tests verifying package imports, configuration, logging redaction, exceptions, and entry point execution.
- **Development Conventions**: Centralized `__version__ = "0.1.0"` in `app/__init__.py`.
- **Architecture Decisions**: Documented ADR-011 (Safe Configuration & Logging Boundaries).

---

## 3. Current Task
M1 implementation review.

---

## 4. Next Task
M1 review and Git commit (manual by user).

---

## 5. Known Issues / Unresolved Items
- **None**: All M1 foundation deliverables implemented and verified with 100% test pass rate. Product functionality (auth, crypto, vault, UI) is intentionally deferred to subsequent milestones per roadmap.

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
- **ADR-011**: Safe Configuration & Logging Boundaries — strict programmatic prohibition of secrets in configuration files and automatic secret redaction in logging filter.
