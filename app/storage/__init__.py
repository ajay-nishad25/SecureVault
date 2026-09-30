"""SecureVault — Storage Subsystem Package.

Architectural Boundary:
This package encapsulates all file format and persistence primitives:
  - 134-byte fixed binary envelope and header parsing (VaultHeader)
  - Associated Authenticated Data (AAD) generation for DEK and Payload
  - Atomic file write with fsync and safe replacement (write_vault_file)
  - Validated file read and truncation detection (read_vault_file)
"""

from app.storage.vault_file import read_vault_file, vault_exists, write_vault_file
from app.storage.vault_format import (
    CURRENT_FORMAT_VERSION,
    HEADER_SIZE,
    MAGIC,
    PAYLOAD_OFFSET,
    VaultHeader,
    extract_aad_dek_from_bytes,
    extract_aad_payload_from_bytes,
)

__all__ = [
    "VaultHeader",
    "HEADER_SIZE",
    "PAYLOAD_OFFSET",
    "MAGIC",
    "CURRENT_FORMAT_VERSION",
    "extract_aad_dek_from_bytes",
    "extract_aad_payload_from_bytes",
    "write_vault_file",
    "read_vault_file",
    "vault_exists",
]
