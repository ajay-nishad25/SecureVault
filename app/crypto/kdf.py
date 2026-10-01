"""SecureVault — Argon2id Key Derivation Function (KDF) Subsystem.

Implements the RFC 9106 Argon2id password-based key derivation function
to derive a 256-bit (32-byte) Key Encryption Key (KEK) from the master password.

CRITICAL SECURITY PRINCIPLES:
  - Argon2id hybrid mode (resistance against GPU brute force & side-channel cache attacks).
  - Production parameters: Memory=64 MiB (65536 KiB), Time=3 iterations, Parallelism=4 lanes.
  - 16-byte random salt generated via OS CSPRNG (secrets module).
  - Master password and derived KEK are NEVER logged, printed, or persisted.
  - Memory wiping in Python is best-effort.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Union

import argon2.exceptions
import argon2.low_level

from app.core.exceptions import (
    InvalidKDFParametersError,
    InvalidPasswordInputError,
    InvalidSaltError,
    SecurityError,
)
from app.core.logging import get_logger
from app.crypto.encryption import zero_buffer

logger = get_logger("crypto.kdf")

# Documented M0 Cryptographic Standards
DEFAULT_MEMORY_COST_KIB = 65536  # 64 MiB
DEFAULT_TIME_COST = 3           # 3 iterations
DEFAULT_PARALLELISM = 4         # 4 lanes
DEFAULT_SALT_LENGTH = 16        # 16 bytes (128 bits)
DEFAULT_HASH_LENGTH = 32        # 32 bytes (256 bits for AES-256 KEK)


@dataclass(frozen=True)
class KDFParameters:
    """Strongly-typed representation of Argon2id KDF parameters."""

    memory_cost: int = DEFAULT_MEMORY_COST_KIB
    time_cost: int = DEFAULT_TIME_COST
    parallelism: int = DEFAULT_PARALLELISM
    salt_length: int = DEFAULT_SALT_LENGTH
    hash_length: int = DEFAULT_HASH_LENGTH

    def validate(self) -> None:
        """Validate KDF parameters against strict cryptographic bounds.

        Raises:
            InvalidKDFParametersError: If any parameter fails validation.
        """
        if not isinstance(self.memory_cost, int) or self.memory_cost < 1024:
            raise InvalidKDFParametersError(
                f"Memory cost must be an integer >= 1024 KiB, got {self.memory_cost}"
            )
        if not isinstance(self.time_cost, int) or self.time_cost < 1:
            raise InvalidKDFParametersError(
                f"Time cost must be an integer >= 1, got {self.time_cost}"
            )
        if not isinstance(self.parallelism, int) or self.parallelism < 1:
            raise InvalidKDFParametersError(
                f"Parallelism must be an integer >= 1, got {self.parallelism}"
            )
        if self.salt_length != DEFAULT_SALT_LENGTH:
            raise InvalidKDFParametersError(
                f"Salt length must be exactly {DEFAULT_SALT_LENGTH} bytes, got {self.salt_length}"
            )
        if self.hash_length != DEFAULT_HASH_LENGTH:
            raise InvalidKDFParametersError(
                f"Derived key length must be exactly {DEFAULT_HASH_LENGTH} bytes, got {self.hash_length}"
            )

    @classmethod
    def default(cls) -> KDFParameters:
        """Return standard production KDF parameters conforming to M0 design."""
        params = cls()
        params.validate()
        return params

    @classmethod
    def fast_for_testing(cls) -> KDFParameters:
        """Return lightweight parameters strictly for high-speed automated unit tests.

        WARNING: NEVER USE IN PRODUCTION. These parameters provide negligible
        resistance against brute-force attacks and are strictly for test suite performance.
        """
        params = cls(
            memory_cost=1024,
            time_cost=1,
            parallelism=1,
            salt_length=DEFAULT_SALT_LENGTH,
            hash_length=DEFAULT_HASH_LENGTH,
        )
        params.validate()
        return params


def generate_salt(length: int = DEFAULT_SALT_LENGTH) -> bytes:
    """Generate a cryptographically random salt using the OS CSPRNG.

    Args:
        length: Desired salt length in bytes (default: 16 bytes).

    Returns:
        bytes: 16 bytes of unpredictable CSPRNG randomness.

    Raises:
        InvalidSaltError: If length does not equal 16.
    """
    if length != DEFAULT_SALT_LENGTH:
        raise InvalidSaltError(
            f"Salt length must be exactly {DEFAULT_SALT_LENGTH} bytes, requested {length}"
        )
    return secrets.token_bytes(length)


def derive_kek(
    password: Union[str, bytes, bytearray],
    salt: bytes,
    parameters: KDFParameters | None = None,
    as_bytearray: bool = False,
) -> Union[bytes, bytearray]:
    """Derive a 256-bit (32-byte) Key Encryption Key (KEK) using Argon2id.

    Args:
        password: Human master password string, bytes, or bytearray.
        salt: 16-byte random cryptographic salt.
        parameters: KDFParameters (defaults to standard M0 production values).
        as_bytearray: If True, returns a mutable bytearray to allow deterministic
            in-place memory zeroing by callers. Defaults to False (bytes).

    Returns:
        bytes | bytearray: Derived 32-byte KEK.

    Raises:
        InvalidPasswordInputError: If the password is empty.
        InvalidSaltError: If the salt length is incorrect.
        InvalidKDFParametersError: If parameters are invalid.
        SecurityError: If low-level KDF derivation fails.

    Security Note:
        The transient password buffer is held in a mutable bytearray and explicitly
        zeroed with zero_buffer() in a finally block. However, callers passing
        Python `str` objects should note that Python immutable strings cannot be
        deterministically erased from interpreter memory.
    """
    params = parameters or KDFParameters.default()
    params.validate()

    if not isinstance(salt, (bytes, bytearray)):
        raise InvalidSaltError("Salt must be provided as bytes.")

    if len(salt) != params.salt_length:
        raise InvalidSaltError(
            f"Invalid salt length: expected {params.salt_length} bytes, got {len(salt)}"
        )

    # Ingest password as transient mutable bytearray
    password_buf: bytearray | None = None
    if isinstance(password, str):
        if not password:
            raise InvalidPasswordInputError("Master password cannot be empty.")
        password_buf = bytearray(password.encode("utf-8"))
    elif isinstance(password, (bytes, bytearray)):
        if not password:
            raise InvalidPasswordInputError("Master password cannot be empty.")
        password_buf = bytearray(password)
    else:
        raise InvalidPasswordInputError("Password must be a string or bytes.")

    logger.debug(
        "Deriving KEK via Argon2id (m=%d KiB, t=%d, p=%d)",
        params.memory_cost,
        params.time_cost,
        params.parallelism,
    )

    try:
        raw_kek = argon2.low_level.hash_secret_raw(
            secret=bytes(password_buf),
            salt=salt,
            time_cost=params.time_cost,
            memory_cost=params.memory_cost,
            parallelism=params.parallelism,
            hash_len=params.hash_length,
            type=argon2.low_level.Type.ID,
        )
    except argon2.exceptions.Argon2Error as err:
        logger.error("Argon2id key derivation error encountered.")
        raise SecurityError(f"Key derivation failed: {err}") from err
    finally:
        # Securely zero the transient mutable password buffer
        if password_buf is not None:
            zero_buffer(password_buf)

    if len(raw_kek) != params.hash_length:
        raise SecurityError(
            f"Derived key length mismatch: expected {params.hash_length} bytes, got {len(raw_kek)}"
        )

    if as_bytearray:
        return bytearray(raw_kek)
    return raw_kek
