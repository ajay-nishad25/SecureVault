"""SecureVault Cryptography Subsystem.

Architectural Boundary:
This package encapsulates all low-level cryptographic primitives:
  - Argon2id Key Derivation Function (RFC 9106)
  - AES-256-GCM Authenticated Encryption with Associated Data (NIST SP 800-38D)
  - CSPRNG random generation (salts, nonces, keys)
  - Best-effort in-memory key hygiene

Note: Full cryptographic engine implementation is scheduled for Milestones M3 and M4.
"""
