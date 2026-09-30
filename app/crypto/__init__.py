"""SecureVault Cryptography Subsystem.

Architectural Boundary:
This package encapsulates all low-level cryptographic primitives:
  - Argon2id Key Derivation Function (RFC 9106) [M3]
  - AES-256-GCM Authenticated Encryption with Associated Data (NIST SP 800-38D) [M4]
  - CSPRNG random generation (salts, nonces, keys)
  - Best-effort in-memory key hygiene
"""

from app.crypto.encryption import (
    KEY_SIZE,
    NONCE_SIZE,
    TAG_SIZE,
    decrypt_payload,
    encrypt_payload,
    generate_dek,
    generate_nonce,
    unwrap_dek,
    wrap_dek,
    zero_buffer,
)
from app.crypto.kdf import KDFParameters, derive_kek, generate_salt

__all__ = [
    "KDFParameters",
    "derive_kek",
    "generate_salt",
    "generate_dek",
    "generate_nonce",
    "wrap_dek",
    "unwrap_dek",
    "encrypt_payload",
    "decrypt_payload",
    "zero_buffer",
    "KEY_SIZE",
    "NONCE_SIZE",
    "TAG_SIZE",
]
