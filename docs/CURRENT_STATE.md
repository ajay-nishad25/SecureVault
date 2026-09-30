# SecureVault — Current Project State

## 1. Milestone Tracking

- **Current Milestone**: `M2 — First-Run Setup Wizard`
- **Status**: **Implementation Complete / Ready for Review**
- **Target Release**: Version 1.0.0 (Windows)
- **Next Milestone**: `M3 — Master Authentication`

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
- **Python Project Environment**: Established local virtual environment (`.venv/`) on Python 3.11.4.
- **Dependency Management**: Established clear separation with `requirements.txt` (`PySide6>=6.5.0`), `requirements-dev.txt` (`pytest>=7.4.0`), and standardized `pyproject.toml`.
- **Package Structure**: Scaffolded clean architecture packages matching M0 boundaries (`app/core/`, `app/crypto/`, `app/storage/`, `app/services/`, `app/models/`, `app/ui/`).
- **Safe Configuration & Logging**: Built `AppConfig` and `SafeLogFilter` with automatic secret redaction (`docs/DECISIONS.md#ADR-011`).
- **Exception Hierarchy**: Built domain exception tree (`SecureVaultError`, `ConfigurationError`, `StorageError`, `SecurityError`, `ValidationError`).

### Milestone 2 (M2 — First-Run Setup Wizard)
- **First-Run Detection**: Implemented `InitializationService` tracking `UNINITIALIZED`, `LOCKED`, and `UNLOCKED` states.
- **Setup Wizard UI**: Created 7-step PySide6 `SetupWizard` (`QWizard`):
  1. *Welcome*: Local-first, offline intro without exaggerated claims.
  2. *Security Architecture*: Core principles (local custody, zero backdoors, no cloud sync in v1).
  3. *No-Recovery Acknowledgement*: Mandatory checkbox with Next button gating.
  4. *Login ID*: Non-secret user identifier with character, length, and reserved name validation.
  5. *Master Password*: Masked input, show/hide toggle, match validation, and advisory local strength meter.
  6. *Final Warning*: Summary of parameters with mandatory confirmation checkbox.
  7. *Completion*: Success notice and transition to `LOCKED` state.
- **Non-Sensitive Initialization State**: Persisted `init_state.json` containing only safe metadata (`initialized`, `login_id`, `created_at`, `format_version`). Zero passwords, hashes, or keys are stored.
- **Cancellation Handling**: Setup cancellation creates zero state files and wipes transient password inputs.
- **Locked State Transition**: Created `LockedView` placeholder showing profile ID and locked status, with dev reset capability.
- **Application Controller**: Built `ApplicationController` orchestrating `UNINITIALIZED -> SetupWizard -> LockedView` and `INITIALIZED -> LockedView`.
- **Testing**: Built 79 passing unit and headless Qt integration tests verifying all validation rules, page completion gates, cancellation, state file safety, and end-to-end onboarding lifecycle.

---

## 3. Current Task
M2 implementation review.

---

## 4. Next Task
M2 review and manual Git commit by user.

---

## 5. Known Issues / Unresolved Items
- **None**: All M2 onboarding deliverables are implemented and tested with 100% pass rate. Real cryptographic key derivation and vault file encryption remain deferred to M3 and M4.

---

## 6. Important Decisions Summary
- **ADR-001 through ADR-010**: Foundational language, GUI, offline, cryptographic, and storage decisions.
- **ADR-011**: Safe Configuration & Logging Boundaries.
- **M2 Foundation Marker**: Temporary non-sensitive JSON marker (`init_state.json`) used for first-run detection until M4 binds initialization directly to the authenticated `.svault` file envelope.
