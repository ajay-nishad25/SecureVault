"""SecureVault Cryptography Subsystem.

Architectural Boundary:
This package encapsulates all low-level cryptographic primitives:
  - Argon2id Key Derivation Function (RFC 9106) [M3]
  - AES-256-GCM Authenticated Encryption with Associated Data (NIST SP 800-38D) [M4]
  - CSPRNG random generation (salts, nonces, keys)
  - Best-effort in-memory key hygiene
"""

from app.crypto.kdf import KDFParameters, derive_kek, generate_salt

__all__ = [
    "KDFParameters",
    "derive_kek",
    "generate_salt",
]
