# SecureVault — Threat Model

## 1. Threat Modeling Methodology

SecureVault applies a structured threat modeling methodology based on STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) tailored specifically for a local, air-gapped, offline desktop application.

Threats are strictly categorized into:
1. **Threats the Application is Designed to Mitigate**: Scenarios where cryptographic guarantees and application safeguards are effective.
2. **Threats Outside Realistic Guarantees**: Fundamental host operating system or hardware compromise scenarios where no user-space software can offer protection.

---

## 2. Threats the Application is Designed to Mitigate

### 2.1 Threat: Physical or Remote Theft of Vault File (`vault.svault`)
- **Threat Scenario**: An adversary copies the `.svault` file via USB, unauthenticated network share, or from a stolen laptop drive.
- **Impact**: Potential exposure of all stored credentials if encryption is weak.
- **Mitigation**:
  - The vault file is protected with **Argon2id** (64 MiB RAM, 3 iterations) and **AES-256-GCM**.
  - Without the master password, brute-force cracking is computationally and economically constrained against passwords with sufficient entropy.
  - No plaintext credentials, usernames, or notes exist on disk.

### 2.2 Threat: Offline Password Guessing & Dictionary Attacks
- **Threat Scenario**: The adversary runs automated dictionary or rainbow table attacks against the extracted `.svault` file.
- **Impact**: Password cracking if KDF is weak or unsalted.
- **Mitigation**:
  - A unique 128-bit CSPRNG salt renders pre-computed rainbow tables ineffective.
  - Argon2id's memory-hardness (64 MiB RAM per attempt) forces adversaries to allocate dedicated physical memory per guess, significantly increasing memory cost and substantially impeding parallel attack throughput on GPUs and ASICs.

### 2.3 Threat: Vault File Tampering, Truncation, or Bit-Flipping
- **Threat Scenario**: An attacker or rogue process modifies bytes in `vault.svault` to cause a parsing error, exploit deserialization vulnerabilities, or alter credential fields.
- **Impact**: Data corruption or execution exploits.
- **Mitigation**:
  - **AES-256-GCM** provides authenticated encryption with 128-bit authentication tags.
  - The static header parameters are bound as Associated Authenticated Data (AAD) for the DEK (`AAD_DEK`), and version/length are bound for the payload (`AAD_PAYLOAD`).
  - Any single bit flip anywhere in the header or ciphertext triggers an immediate authentication tag verification failure; decryption halts before parsing begins.

### 2.4 Threat: Physical Access to Unattended Running Machine
- **Threat Scenario**: A coworker or unauthorized individual approaches the user's desk while the application is left open.
- **Impact**: Immediate visual exposure and copying of stored passwords.
- **Mitigation**:
  - **Inactivity Auto-Lock**: Automatically locks the vault after 10 minutes of idle time.
  - **Quick Lock Shortcut**: `Ctrl+L` enables immediate locking before stepping away.
  - **Default Masking**: Passwords are masked (`••••••••`) on screen until explicitly toggled.

### 2.5 Threat: Accidental Clipboard Snooping
- **Threat Scenario**: The user copies a sensitive password, pastes it into a browser, and forgets the secret remains in the system clipboard. A subsequent application reads the clipboard.
- **Impact**: Credential exposure to non-privileged apps.
- **Mitigation**:
  - **30-Second Auto-Clear Timer**: SecureVault initiates a timer that clears the OS clipboard after 30 seconds.
  - **Watchdog Validation**: SecureVault checks whether the clipboard still contains the copied credential before clearing, preventing accidental erasure of unrelated data copied later.

### 2.6 Threat: Abrupt Crash / Power Outage During Vault Save
- **Threat Scenario**: Computer loses power or crashes during a write operation.
- **Impact**: Zero-byte file or half-written corrupted vault.
- **Mitigation**:
  - **Atomic File Replacement**: Saves are written to `vault.svault.tmp`, synchronized via `os.fsync()`, and swapped into place using `os.replace()`. The active database file is never overwritten directly in-place.

---

## 3. Threats Outside Realistic Guarantees

Honesty in threat modeling is paramount. The following threats reside outside the security boundaries of SecureVault and cannot be prevented by any desktop software running in user space:

### 3.1 Threat: Malware / Rootkits / Keyloggers on the Host Machine
- **Scenario**: The user's operating system has active malware (Trojan, API hook, screen scraper, kernel driver, or hardware keylogger).
- **Reality**: If malware runs under the same user account or administrative context, it can log the master password keystrokes as they are typed into the login window, or capture decrypted memory pages from the process heap.
- **Application Boundary**: SecureVault cannot protect against a compromised operating system. The host environment must be free of active malicious software.

### 3.2 Threat: Memory Forensics (Cold Boot / RAM Dump Analysis)
- **Scenario**: An attacker performs a cold-boot physical memory extraction, or analyzes OS hibernation files (`hiberfil.sys`) / pagefile dumps after the vault has been unlocked.
- **Reality**: While SecureVault actively zeroes mutable buffers and releases references, Python's runtime memory allocator (`pymalloc`) and garbage collection do not guarantee immediate physical overwrite of every byte in physical RAM.
- **Application Boundary**: SecureVault does not claim protection against hardware-level physical forensic extraction or kernel-level memory dumps. Users requiring protection against physical disk extraction should utilize Full Disk Encryption (BitLocker / LUKS) with pre-boot PINs.

### 3.3 Threat: User Master Password Forgotten
- **Scenario**: The user forgets their master password.
- **Reality**: Because there is **no recovery key**, **no backdoor**, and **no cloud reset** in Version 1, mathematical encryption guarantees that the data cannot be decrypted.
- **Application Safeguards**: The user is explicitly warned during initial onboarding and must tick a mandatory acknowledgment checkbox before vault creation.

---

## 4. Threat Summary Matrix

| Threat Description | Category | Mitigated by SecureVault? | Mechanism |
| :--- | :--- | :--- | :--- |
| Stolen `.svault` file | Information Disclosure | **YES** | Argon2id + AES-256-GCM |
| Offline dictionary attack | Information Disclosure | **YES** | Argon2id 64 MiB memory hardness |
| File corruption / bit-flipping | Tampering | **YES** | AEAD authentication tag validation |
| Walk-up access to open PC | Elevation of Privilege | **YES** | 10-minute auto-lock + manual lock |
| Clipboard leakage | Information Disclosure | **YES** | 30s auto-clear countdown |
| Crash during save | Denial of Service | **YES** | Atomic write (`.tmp` + `os.replace`) |
| Host-level keylogger / malware | Information Disclosure | **NO (Out of Scope)** | Relies on OS & AV integrity |
| Physical RAM cold boot attack | Information Disclosure | **NO (Out of Scope)** | Relies on Full Disk Encryption (BitLocker) |
| Lost master password | Denial of Service | **NO (Out of Scope)** | Strict zero-knowledge (No recovery in v1) |
