"""SecureVault — AES-256-GCM Encryption & Key Wrapping Subsystem.

Implements NIST SP 800-38D AES-256-GCM Authenticated Encryption with Associated
Data (AEAD) for:
  1. DEK Wrapping: Encrypting the random 256-bit Data Encryption Key (DEK)
     with the password-derived Key Encryption Key (KEK) using AAD_DEK.
  2. Payload Encryption: Encrypting the serialized vault payload using the
     active DEK with AAD_PAYLOAD.

CRITICAL SECURITY RULES:
  - AES-256-GCM only; never use unauthenticated cipher modes (e.g. ECB, CBC).
  - Every encryption operation MUST generate a fresh, unique 96-bit (12-byte)
    nonce from the OS CSPRNG (secrets.token_bytes).
  - DEK nonces and Payload nonces must NEVER be reused or shared.
  - Authentication tags (128-bit / 16-byte) must be verified prior to returning
    any decrypted plaintext or unwrapped key.
  - Ephemeral sensitive buffers must be zeroed using best-effort memory wiping.
"""

from __future__ import annotations

import secrets
from typing import Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.exceptions import DecryptionError, SecurityError
from app.core.logging import get_logger

logger = get_logger("crypto.encryption")

# Standardized Cryptographic Bounds (NIST SP 800-38D)
KEY_SIZE = 32    # 256 bits (AES-256)
NONCE_SIZE = 12  # 96 bits (Standard GCM nonce)
TAG_SIZE = 16    # 128 bits (GCM authentication tag)


def generate_dek() -> bytes:
    """Generate a cryptographically random 256-bit (32-byte) Data Encryption Key (DEK).

    Uses the operating system's cryptographic random number generator.

    Returns:
        bytes: 32 bytes of uniform random key material.
    """
    return secrets.token_bytes(KEY_SIZE)


def generate_nonce(size: int = NONCE_SIZE) -> bytes:
    """Generate a cryptographically secure random nonce.

    Args:
        size: Nonce size in bytes (default: 12 bytes / 96 bits).

    Returns:
        bytes: Unique random nonce.

    Raises:
        SecurityError: If an invalid nonce size is requested.
    """
    if size != NONCE_SIZE:
        raise SecurityError(f"AES-GCM nonce must be exactly {NONCE_SIZE} bytes, requested {size}")
    return secrets.token_bytes(size)


def wrap_dek(kek: bytes, dek: bytes, aad: bytes) -> tuple[bytes, bytes, bytes]:
    """Wrap (encrypt) the random DEK with the password-derived KEK using AES-256-GCM.

    Args:
        kek: 32-byte Key Encryption Key derived from Argon2id.
        dek: 32-byte random Data Encryption Key.
        aad: Associated Authenticated Data (AAD_DEK = 38-byte public header).

    Returns:
        tuple[bytes, bytes, bytes]: (nonce: 12B, wrapped_dek: 32B, tag: 16B).

    Raises:
        SecurityError: If key sizes or parameters are invalid.
    """
    if len(kek) != KEY_SIZE:
        raise SecurityError(f"KEK must be exactly {KEY_SIZE} bytes, got {len(kek)}")
    if len(dek) != KEY_SIZE:
        raise SecurityError(f"DEK must be exactly {KEY_SIZE} bytes, got {len(dek)}")
    if not isinstance(aad, (bytes, bytearray)):
        raise SecurityError("Associated Authenticated Data (AAD) must be bytes.")

    nonce = generate_nonce(NONCE_SIZE)
    aesgcm = AESGCM(kek)

    # In cryptography, encrypt returns ciphertext + 16-byte tag
    encrypted = aesgcm.encrypt(nonce, dek, aad)
    ciphertext = encrypted[:KEY_SIZE]
    tag = encrypted[KEY_SIZE:]

    if len(ciphertext) != KEY_SIZE or len(tag) != TAG_SIZE:
        raise SecurityError("AES-GCM encryption produced unexpected ciphertext or tag size.")

    return nonce, ciphertext, tag


def unwrap_dek(
    kek: bytes,
    nonce: bytes,
    wrapped_dek: bytes,
    tag: bytes,
    aad: bytes,
) -> bytes:
    """Unwrap (decrypt) the Data Encryption Key (DEK) using the derived KEK.

    Args:
        kek: 32-byte Key Encryption Key derived from Argon2id.
        nonce: 12-byte DEK nonce from vault header.
        wrapped_dek: 32-byte AES-GCM ciphertext of the DEK.
        tag: 16-byte authentication tag from vault header.
        aad: Associated Authenticated Data (AAD_DEK = 38-byte public header).

    Returns:
        bytes: Decrypted 32-byte DEK.

    Raises:
        DecryptionError: If authentication tag verification fails (wrong key or tampering).
        SecurityError: If input lengths are malformed.
    """
    if len(kek) != KEY_SIZE:
        raise SecurityError(f"KEK must be exactly {KEY_SIZE} bytes, got {len(kek)}")
    if len(nonce) != NONCE_SIZE:
        raise SecurityError(f"DEK nonce must be exactly {NONCE_SIZE} bytes, got {len(nonce)}")
    if len(wrapped_dek) != KEY_SIZE:
        raise SecurityError(f"Wrapped DEK must be exactly {KEY_SIZE} bytes, got {len(wrapped_dek)}")
    if len(tag) != TAG_SIZE:
        raise SecurityError(f"DEK tag must be exactly {TAG_SIZE} bytes, got {len(tag)}")
    if not isinstance(aad, (bytes, bytearray)):
        raise SecurityError("Associated Authenticated Data (AAD) must be bytes.")

    aesgcm = AESGCM(kek)
    ciphertext_with_tag = wrapped_dek + tag

    try:
        dek = aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
    except InvalidTag as err:
        logger.warning("DEK unwrap failed: authentication tag verification failed.")
        raise DecryptionError(
            "Authentication tag verification failed: incorrect key or corrupted header."
        ) from err

    if len(dek) != KEY_SIZE:
        raise SecurityError(f"Unwrapped DEK has invalid length: expected {KEY_SIZE}, got {len(dek)}")

    return dek


def encrypt_payload(
    dek: bytes,
    plaintext: bytes,
    aad: bytes,
) -> tuple[bytes, bytes, bytes]:
    """Encrypt vault plaintext bytes using the active DEK and AES-256-GCM.

    Args:
        dek: 32-byte active Data Encryption Key.
        plaintext: Raw UTF-8 bytes of vault payload.
        aad: Associated Authenticated Data (AAD_PAYLOAD = 18 bytes).

    Returns:
        tuple[bytes, bytes, bytes]: (nonce: 12B, ciphertext: len(plaintext)B, tag: 16B).

    Raises:
        SecurityError: If DEK size or parameters are invalid.
    """
    if len(dek) != KEY_SIZE:
        raise SecurityError(f"DEK must be exactly {KEY_SIZE} bytes, got {len(dek)}")
    if not isinstance(plaintext, (bytes, bytearray)):
        raise SecurityError("Plaintext payload must be bytes.")
    if not isinstance(aad, (bytes, bytearray)):
        raise SecurityError("Associated Authenticated Data (AAD) must be bytes.")

    nonce = generate_nonce(NONCE_SIZE)
    aesgcm = AESGCM(dek)

    encrypted = aesgcm.encrypt(nonce, bytes(plaintext), aad)
    ciphertext = encrypted[:-TAG_SIZE]
    tag = encrypted[-TAG_SIZE:]

    return nonce, ciphertext, tag


def decrypt_payload(
    dek: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes,
    aad: bytes,
) -> bytes:
    """Decrypt vault payload ciphertext using the active DEK and AES-256-GCM.

    Args:
        dek: 32-byte active Data Encryption Key.
        nonce: 12-byte payload nonce from vault header.
        ciphertext: AES-GCM ciphertext bytes.
        tag: 16-byte authentication tag from vault header.
        aad: Associated Authenticated Data (AAD_PAYLOAD = 18 bytes).

    Returns:
        bytes: Decrypted UTF-8 plaintext bytes.

    Raises:
        DecryptionError: If authentication tag verification fails (corrupted ciphertext or tag).
        SecurityError: If input lengths are malformed.
    """
    if len(dek) != KEY_SIZE:
        raise SecurityError(f"DEK must be exactly {KEY_SIZE} bytes, got {len(dek)}")
    if len(nonce) != NONCE_SIZE:
        raise SecurityError(f"Payload nonce must be exactly {NONCE_SIZE} bytes, got {len(nonce)}")
    if len(tag) != TAG_SIZE:
        raise SecurityError(f"Payload tag must be exactly {TAG_SIZE} bytes, got {len(tag)}")
    if not isinstance(aad, (bytes, bytearray)):
        raise SecurityError("Associated Authenticated Data (AAD) must be bytes.")

    aesgcm = AESGCM(dek)
    ciphertext_with_tag = ciphertext + tag

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
    except InvalidTag as err:
        logger.warning("Payload decryption failed: authentication tag verification failed.")
        raise DecryptionError(
            "Payload authentication failed: corrupted ciphertext or invalid tag."
        ) from err

    return plaintext


def zero_buffer(buffer: Union[bytearray, memoryview]) -> None:
    """Best-effort in-place zeroing of mutable sensitive byte buffers.

    Note:
        In Python, this overwrites the allocated buffer memory. It does not
        guarantee that copies or string representations created during earlier
        operations are physically erased by the OS or garbage collector.
    """
    if isinstance(buffer, (bytearray, memoryview)):
        for i in range(len(buffer)):
            buffer[i] = 0
