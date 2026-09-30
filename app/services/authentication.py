"""SecureVault — Master Authentication Service.

Coordinates master password intake, Argon2id key derivation, and
in-memory Key Encryption Key (KEK) management.

ARCHITECTURAL BOUNDARY:
This service isolates cryptographic operations from the presentation layer:
  UI -> AuthenticationService -> KDF (Argon2id) -> KEK

ZERO-VERIFIER ARCHITECTURE:
In accordance with the M0 security model, SecureVault DOES NOT store a separate
password hash or verifier on disk. Authentication in M4 will be verified by
attempting to unwrap the Data Encryption Key (DEK) with the derived KEK.
In M3, this service establishes the KDF coordination layer and transient
in-memory key lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.exceptions import (
    AuthenticationError,
    InvalidPasswordInputError,
    InvalidSaltError,
    SecurityError,
)
from app.core.logging import get_logger
from app.crypto.kdf import KDFParameters, derive_kek, generate_salt

logger = get_logger("services.authentication")


@dataclass(frozen=True)
class AuthenticationResult:
    """Outcome of an authentication or KEK derivation request."""

    success: bool
    kek: Optional[bytes] = None
    message: str = ""
    error: Optional[str] = None


class AuthenticationService:
    """Manages master password authentication workflow and transient KEK lifecycle."""

    def __init__(self, kdf_parameters: KDFParameters | None = None) -> None:
        self._kdf_params = kdf_parameters or KDFParameters.default()
        self._active_kek: bytearray | None = None

    @property
    def kdf_parameters(self) -> KDFParameters:
        """Return the active KDF parameters."""
        return self._kdf_params

    def has_active_kek(self) -> bool:
        """Check whether an active KEK is retained in session memory."""
        return self._active_kek is not None

    def get_active_kek(self) -> bytes | None:
        """Return the active KEK bytes if authenticated, or None."""
        if self._active_kek is None:
            return None
        return bytes(self._active_kek)

    def derive_key(
        self,
        password: str,
        salt: bytes,
        parameters: KDFParameters | None = None,
    ) -> bytes:
        """Derive the 256-bit KEK directly from password and salt.

        Args:
            password: Master password string.
            salt: 16-byte cryptographic salt.
            parameters: Optional custom KDF parameters (defaults to instance params).

        Returns:
            bytes: Derived 32-byte KEK.

        Raises:
            AuthenticationError: If derivation fails due to invalid inputs or crypto error.
        """
        params = parameters or self._kdf_params
        try:
            kek_bytes = derive_kek(password, salt, params)
            return kek_bytes
        except (InvalidPasswordInputError, InvalidSaltError, SecurityError) as err:
            logger.warning("Master key derivation failed: %s", err)
            raise AuthenticationError(f"Authentication failed: {err}") from err

    def authenticate(
        self,
        password: str,
        salt: bytes | None = None,
    ) -> AuthenticationResult:
        """Execute master password authentication.

        In Milestone 3 (M3), this derives the 256-bit KEK and stores it in
        session memory. Milestone 4 (M4) will extend this method to unwrap the
        persisted vault DEK.

        Args:
            password: User-entered master password.
            salt: 16-byte salt (if None, a fresh salt is generated for initial setup).

        Returns:
            AuthenticationResult: Containing success status and derived KEK.
        """
        if not password:
            return AuthenticationResult(
                success=False,
                error="Master password cannot be empty.",
            )

        active_salt = salt or generate_salt()

        try:
            raw_kek = self.derive_key(password, active_salt)
            # Store in session memory as mutable bytearray for best-effort zeroing on lock
            self._active_kek = bytearray(raw_kek)
            logger.info("Master authentication KEK derived successfully.")
            return AuthenticationResult(
                success=True,
                kek=raw_kek,
                message="Master password KEK derived successfully.",
            )
        except AuthenticationError as err:
            return AuthenticationResult(
                success=False,
                error=str(err),
            )

    def clear_session(self) -> None:
        """Clear the active in-memory KEK buffer.

        Applies best-effort memory zeroing on the mutable bytearray before release.
        """
        if self._active_kek is not None:
            # Best-effort overwrite with zeros
            for i in range(len(self._active_kek)):
                self._active_kek[i] = 0
            self._active_kek = None
            logger.info("Session KEK purged from memory.")
