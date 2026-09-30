"""SecureVault — Unit & Golden Tests for 134-byte Vault Binary Header.

Verifies:
  - Exact header size = 134 bytes (0x86).
  - Exact byte-by-byte field offsets matching docs/DATA_FORMAT.md.
  - Golden deterministic test fixture.
  - Serialization and deserialization roundtrip fidelity.
  - Rejection of corrupted magic, unsupported versions, invalid KDF parameters.
  - AAD_DEK (38 bytes) and AAD_PAYLOAD (18 bytes) extraction exactness.
"""

import struct
import pytest

from app.core.exceptions import (
    CorruptedVaultError,
    InvalidKDFParametersError,
    InvalidVaultFormatError,
)
from app.storage.vault_format import (
    AAD_DEK_SIZE,
    AAD_PAYLOAD_SIZE,
    CURRENT_FORMAT_VERSION,
    DEK_NONCE_SIZE,
    DEK_TAG_SIZE,
    HEADER_SIZE,
    KDF_ID_ARGON2ID,
    MAGIC,
    PAYLOAD_NONCE_SIZE,
    PAYLOAD_OFFSET,
    PAYLOAD_TAG_SIZE,
    SALT_SIZE,
    WRAPPED_DEK_SIZE,
    VaultHeader,
    extract_aad_dek_from_bytes,
    extract_aad_payload_from_bytes,
)


@pytest.fixture
def sample_header() -> VaultHeader:
    """Return a valid, fully populated VaultHeader fixture."""
    return VaultHeader(
        magic=MAGIC,
        format_version=CURRENT_FORMAT_VERSION,
        kdf_id=KDF_ID_ARGON2ID,
        kdf_memory=65536,
        kdf_time=3,
        kdf_parallel=4,
        salt_len=SALT_SIZE,
        salt=b"\x01" * SALT_SIZE,
        dek_nonce=b"\x02" * DEK_NONCE_SIZE,
        wrapped_dek=b"\x03" * WRAPPED_DEK_SIZE,
        dek_tag=b"\x04" * DEK_TAG_SIZE,
        payload_len=256,
        payload_nonce=b"\x05" * PAYLOAD_NONCE_SIZE,
        payload_tag=b"\x06" * PAYLOAD_TAG_SIZE,
    )


class TestVaultHeaderLayout:
    """Test byte-level layout, offsets, and golden test fixture."""

    def test_header_size_constant(self) -> None:
        assert HEADER_SIZE == 134
        assert HEADER_SIZE == 0x86
        assert PAYLOAD_OFFSET == 134
        assert PAYLOAD_OFFSET == 0x86

    def test_serialize_produces_exact_134_bytes(self, sample_header: VaultHeader) -> None:
        serialized = sample_header.serialize()
        assert isinstance(serialized, bytes)
        assert len(serialized) == 134
        assert len(serialized) == HEADER_SIZE

    def test_golden_header_byte_offsets(self, sample_header: VaultHeader) -> None:
        """Golden test verifying exact byte offsets as defined in docs/DATA_FORMAT.md."""
        b = sample_header.serialize()

        # 0x00 - 0x07: MAGIC (8 bytes) -> b"SVAULT01"
        assert b[0x00:0x08] == b"SVAULT01"

        # 0x08 - 0x09: FORMAT_VERSION (2 bytes uint16 big-endian) -> 1
        assert struct.unpack(">H", b[0x08:0x0A])[0] == 1

        # 0x0A: KDF_ID (1 byte uint8) -> 1
        assert b[0x0A] == 1

        # 0x0B - 0x0E: KDF_MEMORY (4 bytes uint32 big-endian) -> 65536
        assert struct.unpack(">I", b[0x0B:0x0F])[0] == 65536

        # 0x0F - 0x12: KDF_TIME (4 bytes uint32 big-endian) -> 3
        assert struct.unpack(">I", b[0x0F:0x13])[0] == 3

        # 0x13 - 0x14: KDF_PARALLEL (2 bytes uint16 big-endian) -> 4
        assert struct.unpack(">H", b[0x13:0x15])[0] == 4

        # 0x15: SALT_LEN (1 byte uint8) -> 16
        assert b[0x15] == 16

        # 0x16 - 0x25: SALT (16 bytes) -> b"\x01" * 16
        assert b[0x16:0x26] == b"\x01" * 16

        # 0x26 - 0x31: DEK_NONCE (12 bytes) -> b"\x02" * 12
        assert b[0x26:0x32] == b"\x02" * 12

        # 0x32 - 0x51: WRAPPED_DEK (32 bytes) -> b"\x03" * 32
        assert b[0x32:0x52] == b"\x03" * 32

        # 0x52 - 0x61: DEK_TAG (16 bytes) -> b"\x04" * 16
        assert b[0x52:0x62] == b"\x04" * 16

        # 0x62 - 0x69: PAYLOAD_LEN (8 bytes uint64 big-endian) -> 256
        assert struct.unpack(">Q", b[0x62:0x6A])[0] == 256

        # 0x6A - 0x75: PAYLOAD_NONCE (12 bytes) -> b"\x05" * 12
        assert b[0x6A:0x76] == b"\x05" * 12

        # 0x76 - 0x85: PAYLOAD_TAG (16 bytes) -> b"\x06" * 16
        assert b[0x76:0x86] == b"\x06" * 16

        # End of header must be offset 0x86 (134)
        assert len(b) == 0x86

    def test_roundtrip_serialization_deserialization(self, sample_header: VaultHeader) -> None:
        raw = sample_header.serialize()
        parsed = VaultHeader.parse(raw)

        assert parsed.magic == sample_header.magic
        assert parsed.format_version == sample_header.format_version
        assert parsed.kdf_id == sample_header.kdf_id
        assert parsed.kdf_memory == sample_header.kdf_memory
        assert parsed.kdf_time == sample_header.kdf_time
        assert parsed.kdf_parallel == sample_header.kdf_parallel
        assert parsed.salt_len == sample_header.salt_len
        assert parsed.salt == sample_header.salt
        assert parsed.dek_nonce == sample_header.dek_nonce
        assert parsed.wrapped_dek == sample_header.wrapped_dek
        assert parsed.dek_tag == sample_header.dek_tag
        assert parsed.payload_len == sample_header.payload_len
        assert parsed.payload_nonce == sample_header.payload_nonce
        assert parsed.payload_tag == sample_header.payload_tag


class TestAADDefinitions:
    """Test Associated Authenticated Data extraction exactness."""

    def test_aad_dek_length_and_content(self, sample_header: VaultHeader) -> None:
        raw = sample_header.serialize()
        aad = sample_header.compute_aad_dek()

        assert len(aad) == 38
        assert len(aad) == AAD_DEK_SIZE
        assert aad == raw[:0x26]
        assert aad == extract_aad_dek_from_bytes(raw)

    def test_aad_payload_length_and_content(self, sample_header: VaultHeader) -> None:
        raw = sample_header.serialize()
        aad = sample_header.compute_aad_payload()

        assert len(aad) == 18
        assert len(aad) == AAD_PAYLOAD_SIZE
        # MAGIC (8B) + FORMAT_VERSION (2B) + PAYLOAD_LEN (8B)
        expected = raw[0x00:0x0A] + raw[0x62:0x6A]
        assert aad == expected
        assert aad == extract_aad_payload_from_bytes(raw)


class TestHeaderValidationAndRejection:
    """Test fail-secure rejection of invalid or corrupted header buffers."""

    def test_reject_invalid_magic(self, sample_header: VaultHeader) -> None:
        raw = bytearray(sample_header.serialize())
        raw[0:8] = b"BADMAGIC"

        with pytest.raises(InvalidVaultFormatError, match="Invalid vault magic"):
            VaultHeader.parse(bytes(raw))

    def test_reject_unsupported_version(self, sample_header: VaultHeader) -> None:
        raw = bytearray(sample_header.serialize())
        struct.pack_into(">H", raw, 8, 99)

        with pytest.raises(InvalidVaultFormatError, match="Unsupported format version"):
            VaultHeader.parse(bytes(raw))

    def test_reject_unsupported_kdf_id(self, sample_header: VaultHeader) -> None:
        raw = bytearray(sample_header.serialize())
        raw[10] = 0x02  # Not Argon2id

        with pytest.raises(CorruptedVaultError, match="Unsupported KDF ID"):
            VaultHeader.parse(bytes(raw))

    def test_reject_truncated_header(self, sample_header: VaultHeader) -> None:
        raw = sample_header.serialize()
        with pytest.raises(CorruptedVaultError, match="Truncated vault header"):
            VaultHeader.parse(raw[:133])

    def test_reject_invalid_kdf_memory(self, sample_header: VaultHeader) -> None:
        raw = bytearray(sample_header.serialize())
        struct.pack_into(">I", raw, 11, 512)  # Less than 1024 KiB

        with pytest.raises(InvalidKDFParametersError, match="Invalid KDF parameters"):
            VaultHeader.parse(bytes(raw))

    def test_to_kdf_parameters_conversion(self, sample_header: VaultHeader) -> None:
        params = sample_header.to_kdf_parameters()
        assert params.memory_cost == sample_header.kdf_memory
        assert params.time_cost == sample_header.kdf_time
        assert params.parallelism == sample_header.kdf_parallel
        assert params.salt_length == sample_header.salt_len
        assert params.hash_length == 32
