"""SecureVault — Unit Tests for AES-256-GCM Encryption & Key Wrapping.

Verifies:
  - DEK generation (32 bytes, cryptographically random).
  - Nonce generation (12 bytes, unique per operation).
  - DEK wrapping & unwrapping with KEK and AAD_DEK.
  - Payload encryption & decryption with DEK and AAD_PAYLOAD.
  - Fail-secure behavior upon tampering with nonce, ciphertext, tag, or AAD.
  - In-place buffer zeroing helper.
"""

import pytest

from app.core.exceptions import DecryptionError, SecurityError
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


class TestDEKAndNonceGeneration:
    """Test cryptographic generation of DEKs and nonces."""

    def test_dek_length_and_type(self) -> None:
        dek = generate_dek()
        assert isinstance(dek, bytes)
        assert len(dek) == KEY_SIZE
        assert len(dek) == 32

    def test_dek_randomness(self) -> None:
        deks = {generate_dek() for _ in range(50)}
        assert len(deks) == 50

    def test_nonce_length_and_type(self) -> None:
        nonce = generate_nonce()
        assert isinstance(nonce, bytes)
        assert len(nonce) == NONCE_SIZE
        assert len(nonce) == 12

    def test_nonce_randomness(self) -> None:
        nonces = {generate_nonce() for _ in range(50)}
        assert len(nonces) == 50

    def test_invalid_nonce_size_raises(self) -> None:
        with pytest.raises(SecurityError, match="must be exactly 12 bytes"):
            generate_nonce(size=16)


class TestDEKWrapping:
    """Test AES-256-GCM key wrapping and unwrapping under KEK and AAD_DEK."""

    @pytest.fixture
    def test_keys(self) -> tuple[bytes, bytes, bytes]:
        kek = generate_dek()
        dek = generate_dek()
        aad = b"test_aad_header_38_bytes_total_padding!!"[:38]
        return kek, dek, aad

    def test_wrap_and_unwrap_roundtrip(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        assert len(nonce) == NONCE_SIZE
        assert len(wrapped_dek) == KEY_SIZE
        assert len(tag) == TAG_SIZE
        assert wrapped_dek != dek  # Ciphertext must differ from plaintext

        unwrapped = unwrap_dek(kek, nonce, wrapped_dek, tag, aad)
        assert unwrapped == dek

    def test_unwrap_wrong_kek_fails(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        wrong_kek = generate_dek()
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        with pytest.raises(DecryptionError, match="verification failed"):
            unwrap_dek(wrong_kek, nonce, wrapped_dek, tag, aad)

    def test_unwrap_tampered_aad_fails(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        tampered_aad = bytearray(aad)
        tampered_aad[0] ^= 0x01

        with pytest.raises(DecryptionError, match="verification failed"):
            unwrap_dek(kek, nonce, wrapped_dek, tag, bytes(tampered_aad))

    def test_unwrap_tampered_ciphertext_fails(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        tampered_cipher = bytearray(wrapped_dek)
        tampered_cipher[0] ^= 0x01

        with pytest.raises(DecryptionError, match="verification failed"):
            unwrap_dek(kek, nonce, bytes(tampered_cipher), tag, aad)

    def test_unwrap_tampered_tag_fails(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        tampered_tag = bytearray(tag)
        tampered_tag[0] ^= 0x01

        with pytest.raises(DecryptionError, match="verification failed"):
            unwrap_dek(kek, nonce, wrapped_dek, bytes(tampered_tag), aad)

    def test_unwrap_tampered_nonce_fails(self, test_keys: tuple[bytes, bytes, bytes]) -> None:
        kek, dek, aad = test_keys
        nonce, wrapped_dek, tag = wrap_dek(kek, dek, aad)

        tampered_nonce = bytearray(nonce)
        tampered_nonce[0] ^= 0x01

        with pytest.raises(DecryptionError, match="verification failed"):
            unwrap_dek(kek, bytes(tampered_nonce), wrapped_dek, tag, aad)

    def test_invalid_key_lengths_raise(self) -> None:
        short_key = b"short_key"
        valid_key = generate_dek()
        aad = b"aad"

        with pytest.raises(SecurityError, match="KEK must be exactly 32 bytes"):
            wrap_dek(short_key, valid_key, aad)

        with pytest.raises(SecurityError, match="DEK must be exactly 32 bytes"):
            wrap_dek(valid_key, short_key, aad)


class TestPayloadEncryption:
    """Test AES-256-GCM payload encryption and decryption."""

    @pytest.fixture
    def setup_data(self) -> tuple[bytes, bytes, bytes]:
        dek = generate_dek()
        plaintext = b'{"schema_version": 1, "items": [{"title": "secret_entry"}]}'
        aad = b"18_bytes_aad_payl!"
        return dek, plaintext, aad

    def test_payload_encryption_roundtrip(self, setup_data: tuple[bytes, bytes, bytes]) -> None:
        dek, plaintext, aad = setup_data
        nonce, ciphertext, tag = encrypt_payload(dek, plaintext, aad)

        assert len(nonce) == NONCE_SIZE
        assert len(ciphertext) == len(plaintext)
        assert len(tag) == TAG_SIZE
        assert plaintext not in ciphertext

        decrypted = decrypt_payload(dek, nonce, ciphertext, tag, aad)
        assert decrypted == plaintext

    def test_payload_wrong_dek_fails(self, setup_data: tuple[bytes, bytes, bytes]) -> None:
        dek, plaintext, aad = setup_data
        wrong_dek = generate_dek()
        nonce, ciphertext, tag = encrypt_payload(dek, plaintext, aad)

        with pytest.raises(DecryptionError, match="Payload authentication failed"):
            decrypt_payload(wrong_dek, nonce, ciphertext, tag, aad)

    def test_payload_tampered_ciphertext_fails(self, setup_data: tuple[bytes, bytes, bytes]) -> None:
        dek, plaintext, aad = setup_data
        nonce, ciphertext, tag = encrypt_payload(dek, plaintext, aad)

        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF

        with pytest.raises(DecryptionError, match="Payload authentication failed"):
            decrypt_payload(dek, nonce, bytes(tampered), tag, aad)

    def test_payload_tampered_tag_fails(self, setup_data: tuple[bytes, bytes, bytes]) -> None:
        dek, plaintext, aad = setup_data
        nonce, ciphertext, tag = encrypt_payload(dek, plaintext, aad)

        tampered_tag = bytearray(tag)
        tampered_tag[-1] ^= 0xFF

        with pytest.raises(DecryptionError, match="Payload authentication failed"):
            decrypt_payload(dek, nonce, ciphertext, bytes(tampered_tag), aad)

    def test_payload_tampered_aad_fails(self, setup_data: tuple[bytes, bytes, bytes]) -> None:
        dek, plaintext, aad = setup_data
        nonce, ciphertext, tag = encrypt_payload(dek, plaintext, aad)

        tampered_aad = bytearray(aad)
        tampered_aad[0] ^= 0x55

        with pytest.raises(DecryptionError, match="Payload authentication failed"):
            decrypt_payload(dek, nonce, ciphertext, tag, bytes(tampered_aad))


class TestMemoryZeroing:
    """Test best-effort in-place buffer zeroing."""

    def test_zero_buffer_clears_memory(self) -> None:
        buf = bytearray(b"highly_sensitive_dek_material_32")
        assert any(b != 0 for b in buf)

        zero_buffer(buf)

        assert len(buf) == 32
        assert all(b == 0 for b in buf)
