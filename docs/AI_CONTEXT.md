# SecureVault — AI Agent Context & Handoff Guide

> **PRIMARY DIRECTIVE**: Read this file first, then inspect [CURRENT_STATE.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md) before continuing or touching any code.

---

## 1. Project Purpose
SecureVault is an open-source, completely offline, zero-cloud desktop password manager. It allows users to store, manage, search, and generate credentials locally within a single encrypted binary file (`vault.svault`), requiring no internet connectivity, accounts, or remote servers.

---

## 2. Technology Stack & Platform
- **Language**: Python 3.11+
- **GUI Framework**: PySide6 (Qt 6 for Python)
- **Cryptography**: `cryptography` (AES-256-GCM AEAD), `argon2-cffi` (Argon2id KDF), standard `secrets` CSPRNG
- **Platform**: Windows 10/11 64-bit first (`%LOCALAPPDATA%\SecureVault\`); portable design for Linux.

---

## 3. Major Architectural Decisions
1. **Completely Offline**: Zero network sockets, zero telemetry, zero analytics, zero external API calls.
2. **No SQLite**: Persist vault data as a single flat encrypted binary file (`.svault`). Atomic writes via `os.replace`.
3. **No SHA-256 for Credentials**: Stored passwords must be recoverable; use authenticated symmetric encryption (AES-256-GCM).
4. **Argon2id KDF**: 64 MiB memory (`65536 KiB`), 3 iterations, 4 parallelism lanes, 16-byte random salt.
5. **Two-Tier Key Hierarchy**: Master Password derives KEK -> KEK wraps 256-bit DEK -> DEK encrypts JSON payload.
6. **No Recovery Key in v1**: Forgotten master password = permanent data loss. No backdoors, escrow, or reset flows.
7. **Session Security**: 10-minute inactivity auto-lock, manual lock (`Ctrl+L`), best-effort memory clearing on lock.
8. **Clipboard Security**: 30-second auto-clear timer with watchdog protection.

---

## 4. Cryptographic & Vault Storage Model
- **Fixed Header Size**: Exactly 134 bytes (`0x86`). Offsets `0x00 - 0x85`. Payload ciphertext starts at offset `134` (`0x86`).
- **Decoupled AAD**:
  - `AAD_DEK`: First 38 bytes (`0x00 - 0x25`: `MAGIC` through `SALT`).
  - `AAD_PAYLOAD`: 18 bytes (`MAGIC` [8B] + `FORMAT_VERSION` [2B] + `PAYLOAD_LEN` [8B]).
  - *Key Feature*: Changing the master password re-wraps the DEK without invalidating or re-encrypting the payload.
- **Strict Settings Boundary**: `settings.json` contains only non-sensitive UI preferences. Master passwords, keys, and credentials must **NEVER** be stored in plaintext settings.

---

## 5. Milestone Status
- **Current Milestone**: `M0 — Architecture & Security Design` (Ready to Freeze / Commit).
- **Next Milestone**: `M1 — Project Skeleton & Documentation System`.
- *Do not begin M1 or write implementation code without user instruction.*

---

## 6. Critical Security Constraints & Rules for AI Agents
1. **Never Invent Custom Cryptography**: Use only standard primitives from `cryptography` and `argon2-cffi`.
2. **Never Implement Prematurely**: Follow [DEVELOPMENT_ROADMAP.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DEVELOPMENT_ROADMAP.md) sequentially. Do not skip milestones.
3. **Never Log Sensitive Secrets**: Master passwords, keys, and credentials must never be printed or logged.
4. **Never Introduce Network Dependencies**: No `urllib`, `requests`, `aiohttp`, `socket`, or cloud SDKs.
5. **No Overclaims**: Do not describe Python memory clearing as "guaranteed physical erasure"; it is best-effort.
6. **Important Files to Consult**:
   - [CURRENT_STATE.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/CURRENT_STATE.md) (Check this before every turn)
   - [DECISIONS.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DECISIONS.md) (ADRs 001–010)
   - [DATA_FORMAT.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/DATA_FORMAT.md) (Binary layout & AAD)
   - [SECURITY_MODEL.md](file:///c:/Users/Ajay%20Nishad/Documents/SecureVault/docs/SECURITY_MODEL.md) (Boundaries & limitations)
