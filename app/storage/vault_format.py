"""SecureVault — Vault Binary Format & 134-byte Header Subsystem.

Defines the exact binary structure, serialization, deserialization, and
Associated Authenticated Data (AAD) generation for the .svault binary envelope.

SPECIFICATION COMPLIANCE (docs/DATA_FORMAT.md):
  - Fixed Header Size: EXACTLY 134 bytes (0x86).
  - Payload Offset: 0x86 (byte 134).
  - All multi-byte numeric fields are Big-Endian.
  - MAGIC: 8 bytes ASCII (b"SVAULT01").
  - FORMAT_VERSION: 2 bytes uint16 (currently 1).
  - KDF_ID: 1 byte uint8 (0x01 = Argon2id).
  - AAD_DEK: 38 bytes (file_bytes[0x00:0x26]).
  - AAD_PAYLOAD: 18 bytes (file_bytes[0x00:0x0A] || file_bytes[0x62:0x6A]).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from app.core.exceptions import (
    CorruptedVaultError,
    InvalidKDFParametersError,
    InvalidVaultFormatError,
)
from app.crypto.kdf import (
    DEFAULT_HASH_LENGTH,
    DEFAULT_MEMORY_COST_KIB,
    DEFAULT_PARALLELISM,
    DEFAULT_SALT_LENGTH,
    DEFAULT_TIME_COST,
    KDFParameters,
)

# Binary Layout Constants
MAGIC = b"SVAULT01"
CURRENT_FORMAT_VERSION = 1
KDF_ID_ARGON2ID = 1

HEADER_SIZE = 134       # 0x86 bytes
PAYLOAD_OFFSET = 0x86   # 134 bytes

SALT_SIZE = 16
DEK_NONCE_SIZE = 12
WRAPPED_DEK_SIZE = 32
DEK_TAG_SIZE = 16
PAYLOAD_NONCE_SIZE = 12
PAYLOAD_TAG_SIZE = 16

# Offsets for AAD Slicing
AAD_DEK_SIZE = 38           # 0x00 to 0x26
AAD_PAYLOAD_PREFIX_SIZE = 10 # 0x00 to 0x0A (MAGIC 8B + FORMAT_VERSION 2B)
PAYLOAD_LEN_OFFSET = 98     # 0x62
PAYLOAD_LEN_SIZE = 8        # 0x62 to 0x6A (uint64)
AAD_PAYLOAD_SIZE = 18       # 10 + 8 = 18 bytes

# Struct packing format: Big-Endian (>), no padding
# 8s  : MAGIC (8 bytes)
# H   : FORMAT_VERSION (2 bytes uint16)
# B   : KDF_ID (1 byte uint8)
# I   : KDF_MEMORY (4 bytes uint32)
# I   : KDF_TIME (4 bytes uint32)
# H   : KDF_PARALLEL (2 bytes uint16)
# B   : SALT_LEN (1 byte uint8)
# 16s : SALT (16 bytes)
# 12s : DEK_NONCE (12 bytes)
# 32s : WRAPPED_DEK (32 bytes)
# 16s : DEK_TAG (16 bytes)
# Q   : PAYLOAD_LEN (8 bytes uint64)
# 12s : PAYLOAD_NONCE (12 bytes)
# 16s : PAYLOAD_TAG (16 bytes)
HEADER_STRUCT_FORMAT = ">8s H B I I H B 16s 12s 32s 16s Q 12s 16s"


@dataclass(frozen=True)
class VaultHeader:
    """Strongly-typed representation of the 134-byte fixed .svault header."""

    magic: bytes
    format_version: int
    kdf_id: int
    kdf_memory: int
    kdf_time: int
    kdf_parallel: int
    salt_len: int
    salt: bytes
    dek_nonce: bytes
    wrapped_dek: bytes
    dek_tag: bytes
    payload_len: int
    payload_nonce: bytes
    payload_tag: bytes

    def validate(self) -> None:
        """Validate header fields against specification constraints.

        Raises:
            InvalidVaultFormatError: If magic or version is invalid.
            CorruptedVaultError: If any binary field size or value is invalid.
        """
        if self.magic != MAGIC:
            raise InvalidVaultFormatError(
                f"Invalid vault magic: expected {MAGIC!r}, got {self.magic!r}"
            )
        if self.format_version != CURRENT_FORMAT_VERSION:
            raise InvalidVaultFormatError(
                f"Unsupported format version: expected {CURRENT_FORMAT_VERSION}, got {self.format_version}"
            )
        if self.kdf_id != KDF_ID_ARGON2ID:
            raise CorruptedVaultError(
                f"Unsupported KDF ID: expected {KDF_ID_ARGON2ID} (Argon2id), got {self.kdf_id}"
            )
        if self.salt_len != SALT_SIZE or len(self.salt) != SALT_SIZE:
            raise CorruptedVaultError(
                f"Invalid salt length: expected {SALT_SIZE} bytes, got salt_len={self.salt_len}, len(salt)={len(self.salt)}"
            )
        if len(self.dek_nonce) != DEK_NONCE_SIZE:
            raise CorruptedVaultError(
                f"Invalid DEK nonce size: expected {DEK_NONCE_SIZE} bytes, got {len(self.dek_nonce)}"
            )
        if len(self.wrapped_dek) != WRAPPED_DEK_SIZE:
            raise CorruptedVaultError(
                f"Invalid wrapped DEK size: expected {WRAPPED_DEK_SIZE} bytes, got {len(self.wrapped_dek)}"
            )
        if len(self.dek_tag) != DEK_TAG_SIZE:
            raise CorruptedVaultError(
                f"Invalid DEK tag size: expected {DEK_TAG_SIZE} bytes, got {len(self.dek_tag)}"
            )
        if len(self.payload_nonce) != PAYLOAD_NONCE_SIZE:
            raise CorruptedVaultError(
                f"Invalid payload nonce size: expected {PAYLOAD_NONCE_SIZE} bytes, got {len(self.payload_nonce)}"
            )
        if len(self.payload_tag) != PAYLOAD_TAG_SIZE:
            raise CorruptedVaultError(
                f"Invalid payload tag size: expected {PAYLOAD_TAG_SIZE} bytes, got {len(self.payload_tag)}"
            )
        if self.payload_len < 0:
            raise CorruptedVaultError(f"Negative payload length: {self.payload_len}")

        # Validate KDF parameter bounds
        if self.kdf_memory < 1024 or self.kdf_time < 1 or self.kdf_parallel < 1:
            raise InvalidKDFParametersError(
                f"Invalid KDF parameters in header: memory={self.kdf_memory}, time={self.kdf_time}, parallel={self.kdf_parallel}"
            )

    def serialize(self) -> bytes:
        """Serialize header fields into exactly 134 bytes.

        Returns:
            bytes: Exactly 134-byte binary header.

        Raises:
            CorruptedVaultError: If serialization fails or produces incorrect size.
        """
        self.validate()

        packed = struct.pack(
            HEADER_STRUCT_FORMAT,
            self.magic,
            self.format_version,
            self.kdf_id,
            self.kdf_memory,
            self.kdf_time,
            self.kdf_parallel,
            self.salt_len,
            self.salt,
            self.dek_nonce,
            self.wrapped_dek,
            self.dek_tag,
            self.payload_len,
            self.payload_nonce,
            self.payload_tag,
        )

        if len(packed) != HEADER_SIZE:
            raise CorruptedVaultError(
                f"Header serialization size error: expected {HEADER_SIZE} bytes, got {len(packed)}"
            )

        return packed

    @classmethod
    def parse(cls, data: bytes) -> VaultHeader:
        """Deserialize and validate a 134-byte header buffer.

        Args:
            data: Binary buffer of at least 134 bytes.

        Returns:
            VaultHeader: Validated header object.

        Raises:
            CorruptedVaultError: If buffer is truncated or fields are invalid.
            InvalidVaultFormatError: If magic or version is invalid.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise CorruptedVaultError("Header data must be bytes.")
        if len(data) < HEADER_SIZE:
            raise CorruptedVaultError(
                f"Truncated vault header: expected {HEADER_SIZE} bytes, got {len(data)}"
            )

        header_bytes = bytes(data[:HEADER_SIZE])

        try:
            (
                magic,
                format_version,
                kdf_id,
                kdf_memory,
                kdf_time,
                kdf_parallel,
                salt_len,
                salt,
                dek_nonce,
                wrapped_dek,
                dek_tag,
                payload_len,
                payload_nonce,
                payload_tag,
            ) = struct.unpack(HEADER_STRUCT_FORMAT, header_bytes)
        except struct.error as err:
            raise CorruptedVaultError(f"Failed to unpack binary header: {err}") from err

        header = cls(
            magic=magic,
            format_version=format_version,
            kdf_id=kdf_id,
            kdf_memory=kdf_memory,
            kdf_time=kdf_time,
            kdf_parallel=kdf_parallel,
            salt_len=salt_len,
            salt=salt,
            dek_nonce=dek_nonce,
            wrapped_dek=wrapped_dek,
            dek_tag=dek_tag,
            payload_len=payload_len,
            payload_nonce=payload_nonce,
            payload_tag=payload_tag,
        )
        header.validate()
        return header

    def to_kdf_parameters(self) -> KDFParameters:
        """Extract KDFParameters represented by this header.

        Returns:
            KDFParameters: Strongly-typed parameters for Argon2id KEK derivation.
        """
        return KDFParameters(
            memory_cost=self.kdf_memory,
            time_cost=self.kdf_time,
            parallelism=self.kdf_parallel,
            salt_length=self.salt_len,
            hash_length=DEFAULT_HASH_LENGTH,
        )

    def compute_aad_dek(self) -> bytes:
        """Compute the 38-byte Associated Authenticated Data for DEK wrapping (AAD_DEK).

        Definition: file_bytes[0x00 : 0x26] (MAGIC through SALT).
        """
        serialized = self.serialize()
        return serialized[:AAD_DEK_SIZE]

    def compute_aad_payload(self) -> bytes:
        """Compute the 18-byte Associated Authenticated Data for payload encryption (AAD_PAYLOAD).

        Definition: file_bytes[0x00 : 0x0A] || file_bytes[0x62 : 0x6A]
        (MAGIC 8B + FORMAT_VERSION 2B + PAYLOAD_LEN 8B).
        """
        serialized = self.serialize()
        prefix = serialized[:AAD_PAYLOAD_PREFIX_SIZE]
        length_bytes = serialized[PAYLOAD_LEN_OFFSET : PAYLOAD_LEN_OFFSET + PAYLOAD_LEN_SIZE]
        return prefix + length_bytes


def extract_aad_dek_from_bytes(header_bytes: bytes) -> bytes:
    """Extract AAD_DEK directly from raw header bytes.

    Args:
        header_bytes: Header bytes of at least 38 bytes.

    Returns:
        bytes: 38 bytes of AAD_DEK.
    """
    if len(header_bytes) < AAD_DEK_SIZE:
        raise CorruptedVaultError(
            f"Cannot extract AAD_DEK: expected at least {AAD_DEK_SIZE} bytes, got {len(header_bytes)}"
        )
    return header_bytes[:AAD_DEK_SIZE]


def extract_aad_payload_from_bytes(header_bytes: bytes) -> bytes:
    """Extract AAD_PAYLOAD directly from raw header bytes.

    Args:
        header_bytes: Header bytes of at least 106 bytes (up to PAYLOAD_LEN_OFFSET + PAYLOAD_LEN_SIZE).

    Returns:
        bytes: 18 bytes of AAD_PAYLOAD.
    """
    min_required = PAYLOAD_LEN_OFFSET + PAYLOAD_LEN_SIZE
    if len(header_bytes) < min_required:
        raise CorruptedVaultError(
            f"Cannot extract AAD_PAYLOAD: expected at least {min_required} bytes, got {len(header_bytes)}"
        )
    prefix = header_bytes[:AAD_PAYLOAD_PREFIX_SIZE]
    length_bytes = header_bytes[PAYLOAD_LEN_OFFSET : PAYLOAD_LEN_OFFSET + PAYLOAD_LEN_SIZE]
    return prefix + length_bytes
