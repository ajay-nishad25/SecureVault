"""SecureVault — Atomic Vault File I/O Subsystem.

Provides atomic persistence, directory preparation, and integrity-checked
reading for the encrypted .svault file format.

CRITICAL RELIABILITY & SECURITY PRINCIPLES:
  - Atomic Write: Writes first to a temporary file ({path}.tmp), flushes buffer,
    executes OS fsync, closes the handle, then atomically replaces the target.
  - Fail-Safe Cleanup: Temporary files are cleaned up on write failures.
  - No Truncation: Reading verifies header bounds and enforces exact payload
    length matching against PAYLOAD_LEN in the binary header.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.exceptions import CorruptedVaultError, StorageError, VaultNotFoundError
from app.core.logging import get_logger
from app.storage.vault_format import HEADER_SIZE, VaultHeader

logger = get_logger("storage.vault_file")


def vault_exists(path: Path) -> bool:
    """Check if a valid vault file exists at the given path."""
    return path.exists() and path.is_file()


def write_vault_file(
    path: Path,
    header_bytes: bytes,
    payload_ciphertext: bytes,
) -> None:
    """Atomically write header and ciphertext to the vault file.

    Workflow:
      1. Ensure target directory exists.
      2. Write data to temporary file ({path}.tmp).
      3. Flush user-space buffer and fsync to disk.
      4. Close file handle.
      5. Atomically replace target file using os.replace.

    Args:
        path: Target .svault destination path.
        header_bytes: Exactly 134-byte serialized VaultHeader.
        payload_ciphertext: AES-256-GCM encrypted payload ciphertext.

    Raises:
        StorageError: If atomic file write or directory operations fail.
    """
    if len(header_bytes) != HEADER_SIZE:
        raise StorageError(
            f"Invalid header size for vault write: expected {HEADER_SIZE} bytes, got {len(header_bytes)}"
        )

    # Ensure parent directory exists
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        logger.error("Failed to create vault directory '%s': %s", path.parent, err)
        raise StorageError(f"Could not create vault directory: {err}") from err

    tmp_path = path.with_name(f"{path.name}.tmp")

    try:
        with open(tmp_path, "wb") as f:
            f.write(header_bytes)
            f.write(payload_ciphertext)
            f.flush()
            os.fsync(f.fileno())

        # Atomically replace target path
        os.replace(tmp_path, path)
        logger.info("Vault file atomically written to '%s' (%d bytes).", path.name, len(header_bytes) + len(payload_ciphertext))
    except OSError as err:
        logger.error("Atomic write to vault '%s' failed: %s", path, err)
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise StorageError(f"Failed to write vault file atomically: {err}") from err


def read_vault_file(path: Path) -> tuple[bytes, bytes]:
    """Read and validate the raw header and payload ciphertext from a vault file.

    Performs structural integrity verification:
      - Validates file exists.
      - Enforces minimum file size (134 bytes).
      - Parses header and enforces that actual payload length equals PAYLOAD_LEN.

    Args:
        path: Path to the .svault file.

    Returns:
        tuple[bytes, bytes]: (header_bytes: 134B, payload_ciphertext: variable).

    Raises:
        VaultNotFoundError: If the vault file does not exist.
        CorruptedVaultError: If file is truncated or payload length mismatches header.
        StorageError: If read fails due to OS errors.
    """
    if not path.exists() or not path.is_file():
        raise VaultNotFoundError(f"Vault file not found at '{path}'")

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as err:
        logger.error("Failed to read vault file '%s': %s", path, err)
        raise StorageError(f"Could not read vault file: {err}") from err

    if len(data) < HEADER_SIZE:
        raise CorruptedVaultError(
            f"Vault file is truncated: expected at least {HEADER_SIZE} bytes, got {len(data)}"
        )

    header_bytes = data[:HEADER_SIZE]
    payload_ciphertext = data[HEADER_SIZE:]

    # Parse and validate header fields
    header = VaultHeader.parse(header_bytes)

    if len(payload_ciphertext) != header.payload_len:
        raise CorruptedVaultError(
            f"Vault payload length mismatch: header specifies {header.payload_len} bytes, "
            f"file contains {len(payload_ciphertext)} bytes."
        )

    return header_bytes, payload_ciphertext
