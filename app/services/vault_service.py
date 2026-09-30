"""SecureVault — Vault Lifecycle & Decryption Orchestration Service.

Coordinates:
  - Cryptographic vault initialization and creation (.svault)
  - Key derivation and authenticated DEK unwrapping (unlocking)
  - AES-256-GCM authenticated payload decryption
  - Ephemeral in-memory decrypted vault session lifecycle
  - Best-effort in-memory key hygiene upon lock

CRITICAL SECURITY RULES:
  - Master password and KEK are NEVER persisted.
  - DEK is persisted ONLY in wrapped form under AES-256-GCM + AAD_DEK.
  - Decrypted vault payload and raw DEK reside in memory ONLY while unlocked.
  - Wrong password detection occurs naturally through authenticated DEK unwrapping failure.
"""

from __future__ import annotations

import json
import struct
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

from app.core.config import AppConfig
from app.core.exceptions import (
    AuthenticationError,
    CorruptedVaultError,
    DecryptionError,
    InvalidPasswordInputError,
    SecurityError,
    VaultLockedError,
)
from app.core.logging import get_logger
from app.crypto.encryption import (
    KEY_SIZE,
    decrypt_payload,
    encrypt_payload,
    generate_dek,
    unwrap_dek,
    wrap_dek,
    zero_buffer,
)
from app.crypto.kdf import KDFParameters, derive_kek, generate_salt
from app.storage.vault_file import read_vault_file, vault_exists, write_vault_file
from app.storage.vault_format import (
    CURRENT_FORMAT_VERSION,
    HEADER_SIZE,
    KDF_ID_ARGON2ID,
    MAGIC,
    VaultHeader,
    extract_aad_dek_from_bytes,
    extract_aad_payload_from_bytes,
)

logger = get_logger("services.vault")


def create_empty_vault_payload() -> bytes:
    """Create a minimal, valid UTF-8 JSON vault envelope containing an empty credential list.

    Conforms to the schema defined in docs/DATA_FORMAT.md Section 4.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "schema_version": 1,
        "vault_id": str(uuid.uuid4()),
        "created_at": now_iso,
        "updated_at": now_iso,
        "items": [],
    }
    return json.dumps(data, indent=2).encode("utf-8")


@dataclass
class DecryptedVault:
    """In-memory representation of an active, unlocked vault."""

    payload: dict[str, Any]
    raw_json: str
    dek: bytearray
    header: VaultHeader
    vault_path: Path
    is_locked: bool = False

    def lock(self) -> None:
        """Lock the vault session and overwrite active in-memory key buffers."""
        if not self.is_locked:
            zero_buffer(self.dek)
            self.payload.clear()
            self.raw_json = ""
            self.is_locked = True
            logger.info("Vault session locked and in-memory key buffers zeroed.")

    @property
    def item_count(self) -> int:
        """Return the number of stored credentials."""
        if self.is_locked:
            return 0
        return len(self.payload.get("items", []))

    @property
    def vault_id(self) -> str:
        """Return the unique vault identifier."""
        if self.is_locked:
            return ""
        return str(self.payload.get("vault_id", ""))


class VaultService:
    """Orchestrates encrypted vault creation, loading, unlocking, and session locking."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig()
        self._active_vault: DecryptedVault | None = None

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def active_vault(self) -> DecryptedVault | None:
        """Return the currently unlocked vault, or None if locked."""
        if self._active_vault and not self._active_vault.is_locked:
            return self._active_vault
        return None

    def is_vault_created(self, vault_path: Path | None = None) -> bool:
        """Check whether the encrypted vault file exists on disk."""
        target_path = vault_path or self._config.vault_path
        return vault_exists(target_path)

    def create_vault(
        self,
        master_password: Union[str, bytes],
        vault_path: Path | None = None,
        kdf_params: KDFParameters | None = None,
    ) -> DecryptedVault:
        """Create a new encrypted .svault database file.

        Workflow:
          1. Generate a fresh 16-byte random salt.
          2. Derive 32-byte KEK via Argon2id.
          3. Generate random 32-byte DEK.
          4. Compute AAD_DEK (first 38 bytes of public header).
          5. Wrap DEK under KEK with AES-256-GCM.
          6. Generate initial empty JSON envelope.
          7. Compute AAD_PAYLOAD (18 bytes).
          8. Encrypt payload under DEK with AES-256-GCM.
          9. Assemble and serialize exact 134-byte VaultHeader.
          10. Write file atomically via temporary file and replace.
          11. Zero temporary KEK and return unlocked DecryptedVault.

        Args:
            master_password: Master password string or bytes.
            vault_path: Optional custom path (defaults to config.vault_path).
            kdf_params: Optional KDF parameters (defaults to production M0).

        Returns:
            DecryptedVault: Active unlocked vault session.

        Raises:
            InvalidPasswordInputError: If master password is empty.
            StorageError: If atomic file write fails.
            SecurityError: If cryptographic derivation fails.
        """
        if not master_password:
            raise InvalidPasswordInputError("Master password cannot be empty.")

        target_path = vault_path or self._config.vault_path
        params = kdf_params or KDFParameters.default()
        params.validate()

        logger.info("Initializing new encrypted vault at '%s'.", target_path.name)

        # 1. Salt & KEK Derivation
        salt = generate_salt(params.salt_length)
        kek = derive_kek(master_password, salt, params)

        # 2. Random DEK Generation
        dek = generate_dek()

        # 3. Compute AAD_DEK (MAGIC + FORMAT_VERSION + KDF fields + SALT)
        # Struct: >8s H B I I H B 16s (38 bytes)
        public_header_prefix = struct.pack(
            ">8s H B I I H B 16s",
            MAGIC,
            CURRENT_FORMAT_VERSION,
            KDF_ID_ARGON2ID,
            params.memory_cost,
            params.time_cost,
            params.parallelism,
            len(salt),
            salt,
        )
        aad_dek = public_header_prefix

        # 4. Wrap DEK
        dek_nonce, wrapped_dek, dek_tag = wrap_dek(kek, dek, aad_dek)

        # 5. Generate and Encrypt Initial Payload
        plaintext_payload = create_empty_vault_payload()
        payload_len = len(plaintext_payload)

        # 6. Compute AAD_PAYLOAD (MAGIC 8B + FORMAT_VERSION 2B + PAYLOAD_LEN 8B)
        aad_payload = struct.pack(
            ">8s H Q",
            MAGIC,
            CURRENT_FORMAT_VERSION,
            payload_len,
        )

        payload_nonce, payload_ciphertext, payload_tag = encrypt_payload(
            dek,
            plaintext_payload,
            aad_payload,
        )

        # 7. Assemble 134-byte VaultHeader
        header = VaultHeader(
            magic=MAGIC,
            format_version=CURRENT_FORMAT_VERSION,
            kdf_id=KDF_ID_ARGON2ID,
            kdf_memory=params.memory_cost,
            kdf_time=params.time_cost,
            kdf_parallel=params.parallelism,
            salt_len=len(salt),
            salt=salt,
            dek_nonce=dek_nonce,
            wrapped_dek=wrapped_dek,
            dek_tag=dek_tag,
            payload_len=payload_len,
            payload_nonce=payload_nonce,
            payload_tag=payload_tag,
        )

        header_bytes = header.serialize()

        # 8. Atomically Persist to Disk
        write_vault_file(target_path, header_bytes, payload_ciphertext)

        # Best-effort zeroing of temporary KEK buffer
        if isinstance(kek, (bytearray, memoryview)):
            zero_buffer(kek)
        kek = b"\x00" * len(kek)

        logger.info("Encrypted vault successfully created and persisted.")

        # Parse initial payload
        payload_dict = json.loads(plaintext_payload.decode("utf-8"))
        decrypted_vault = DecryptedVault(
            payload=payload_dict,
            raw_json=plaintext_payload.decode("utf-8"),
            dek=bytearray(dek),
            header=header,
            vault_path=target_path,
        )
        self._active_vault = decrypted_vault
        return decrypted_vault

    def unlock_vault(
        self,
        master_password: Union[str, bytes],
        vault_path: Path | None = None,
    ) -> DecryptedVault:
        """Unlock and decrypt an existing .svault file using the master password.

        Workflow:
          1. Read binary header and payload ciphertext from file.
          2. Parse and validate 134-byte VaultHeader.
          3. Read KDF parameters and salt directly from header.
          4. Derive KEK via Argon2id.
          5. Reconstruct AAD_DEK (first 38 bytes of header).
          6. Attempt AES-256-GCM unwrap of DEK under KEK.
             (Fails with AuthenticationError if password is incorrect).
          7. Reconstruct AAD_PAYLOAD (18 bytes).
          8. Decrypt payload ciphertext under unwrapped DEK.
             (Fails with CorruptedVaultError if payload tag fails).
          9. Parse UTF-8 JSON envelope.
          10. Zero temporary KEK and return DecryptedVault.

        Args:
            master_password: User entered master password.
            vault_path: Optional custom path (defaults to config.vault_path).

        Returns:
            DecryptedVault: Unlocked vault session containing active DEK.

        Raises:
            AuthenticationError: If master password is incorrect.
            CorruptedVaultError: If vault file or payload is corrupted.
            VaultNotFoundError: If vault file does not exist.
        """
        if not master_password:
            raise InvalidPasswordInputError("Master password cannot be empty.")

        target_path = vault_path or self._config.vault_path
        header_bytes, payload_ciphertext = read_vault_file(target_path)

        header = VaultHeader.parse(header_bytes)
        kdf_params = header.to_kdf_parameters()

        # Derive KEK using header's salt and parameters
        kek = derive_kek(master_password, header.salt, kdf_params)

        # Reconstruct AAD_DEK
        aad_dek = extract_aad_dek_from_bytes(header_bytes)

        # Attempt to unwrap DEK
        try:
            dek = unwrap_dek(
                kek=kek,
                nonce=header.dek_nonce,
                wrapped_dek=header.wrapped_dek,
                tag=header.dek_tag,
                aad=aad_dek,
            )
        except DecryptionError as err:
            logger.warning("Vault unlock failed: incorrect master password or corrupted header.")
            # Map low-level decryption failure to domain authentication error
            raise AuthenticationError(
                "Incorrect master password or invalid vault."
            ) from err

        # Reconstruct AAD_PAYLOAD
        aad_payload = extract_aad_payload_from_bytes(header_bytes)

        # Decrypt payload ciphertext
        try:
            plaintext_bytes = decrypt_payload(
                dek=dek,
                nonce=header.payload_nonce,
                ciphertext=payload_ciphertext,
                tag=header.payload_tag,
                aad=aad_payload,
            )
        except DecryptionError as err:
            logger.error("Vault payload decryption failed: authentication tag mismatch.")
            raise CorruptedVaultError(
                "Vault payload authentication failed or corrupted."
            ) from err

        # Parse JSON
        try:
            raw_json = plaintext_bytes.decode("utf-8")
            payload_dict = json.loads(raw_json)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            logger.error("Failed to parse decrypted vault JSON payload: %s", err)
            raise CorruptedVaultError(f"Decrypted vault payload is not valid JSON: {err}") from err

        # Best-effort zeroing of temporary KEK buffer
        if isinstance(kek, (bytearray, memoryview)):
            zero_buffer(kek)
        kek = b"\x00" * len(kek)

        logger.info("Vault successfully unlocked and decrypted for user session.")

        decrypted_vault = DecryptedVault(
            payload=payload_dict,
            raw_json=raw_json,
            dek=bytearray(dek),
            header=header,
            vault_path=target_path,
        )
        self._active_vault = decrypted_vault
        return decrypted_vault

    def save_vault(self, vault: DecryptedVault | None = None) -> None:
        """Persist the active unlocked vault session to disk under AES-256-GCM.

        Re-encrypts the updated JSON payload using the active DEK and updates
        the payload length, nonce, and authentication tag in the 134-byte header.
        The wrapped DEK, salt, and KDF parameters remain completely intact.
        Writes atomically via temporary file and replace.

        Args:
            vault: Optional DecryptedVault instance (defaults to self.active_vault).

        Raises:
            VaultLockedError: If vault is None or locked.
            StorageError: If atomic file write fails.
        """
        target_vault = vault or self._active_vault
        if target_vault is None or target_vault.is_locked:
            raise VaultLockedError("Cannot save vault: active vault session is locked or unavailable.")

        # Update updated_at timestamp in payload envelope
        target_vault.payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Serialize payload to JSON bytes
        plaintext_payload = json.dumps(target_vault.payload, indent=2).encode("utf-8")
        payload_len = len(plaintext_payload)

        # Compute AAD_PAYLOAD (MAGIC 8B + FORMAT_VERSION 2B + PAYLOAD_LEN 8B)
        aad_payload = struct.pack(
            ">8s H Q",
            MAGIC,
            CURRENT_FORMAT_VERSION,
            payload_len,
        )

        # Encrypt payload under DEK with fresh 12-byte CSPRNG nonce
        payload_nonce, payload_ciphertext, payload_tag = encrypt_payload(
            bytes(target_vault.dek),
            plaintext_payload,
            aad_payload,
        )

        # Update header payload metadata (VaultHeader is frozen)
        target_vault.header = replace(
            target_vault.header,
            payload_len=payload_len,
            payload_nonce=payload_nonce,
            payload_tag=payload_tag,
        )

        # Assemble and serialize exact 134-byte VaultHeader
        header_bytes = target_vault.header.serialize()

        # Atomically write to disk
        write_vault_file(target_vault.vault_path, header_bytes, payload_ciphertext)

        target_vault.raw_json = plaintext_payload.decode("utf-8")
        logger.info("Encrypted vault successfully saved and persisted to disk.")

    def lock_vault(self) -> None:
        """Lock the active vault session and wipe in-memory sensitive keys."""
        if self._active_vault:
            self._active_vault.lock()
            self._active_vault = None
            logger.info("Active vault session cleared from VaultService.")
