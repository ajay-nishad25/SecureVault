"""Tests for Argon2id Key Derivation Function (KDF) subsystem."""

import pytest

from app.core.exceptions import (
    InvalidKDFParametersError,
    InvalidPasswordInputError,
    InvalidSaltError,
)
from app.crypto.kdf import (
    DEFAULT_HASH_LENGTH,
    DEFAULT_MEMORY_COST_KIB,
    DEFAULT_PARALLELISM,
    DEFAULT_SALT_LENGTH,
    DEFAULT_TIME_COST,
    KDFParameters,
    derive_kek,
    generate_salt,
)


class TestSaltGeneration:
    """Test suite for cryptographic salt generation."""

    def test_default_salt_length(self) -> None:
        salt = generate_salt()
        assert isinstance(salt, bytes)
        assert len(salt) == DEFAULT_SALT_LENGTH

    def test_salt_is_cryptographically_unpredictable(self) -> None:
        salt1 = generate_salt()
        salt2 = generate_salt()
        assert salt1 != salt2

    def test_invalid_salt_length_rejected(self) -> None:
        with pytest.raises(InvalidSaltError):
            generate_salt(8)
        with pytest.raises(InvalidSaltError):
            generate_salt(32)


class TestKDFParameters:
    """Test suite for KDFParameters typing, presets, and boundary checks."""

    def test_default_parameters_match_m0_specification(self) -> None:
        params = KDFParameters.default()
        assert params.memory_cost == DEFAULT_MEMORY_COST_KIB  # 65536 KiB (64 MiB)
        assert params.time_cost == DEFAULT_TIME_COST          # 3 iterations
        assert params.parallelism == DEFAULT_PARALLELISM      # 4 lanes
        assert params.salt_length == DEFAULT_SALT_LENGTH      # 16 bytes
        assert params.hash_length == DEFAULT_HASH_LENGTH      # 32 bytes (256 bits)

    def test_fast_testing_parameters_preset(self) -> None:
        fast_params = KDFParameters.fast_for_testing()
        assert fast_params.memory_cost == 1024
        assert fast_params.time_cost == 1
        assert fast_params.parallelism == 1
        assert fast_params.salt_length == 16
        assert fast_params.hash_length == 32

    def test_invalid_memory_cost_rejected(self) -> None:
        with pytest.raises(InvalidKDFParametersError):
            KDFParameters(memory_cost=512).validate()

    def test_invalid_time_cost_rejected(self) -> None:
        with pytest.raises(InvalidKDFParametersError):
            KDFParameters(time_cost=0).validate()

    def test_invalid_parallelism_rejected(self) -> None:
        with pytest.raises(InvalidKDFParametersError):
            KDFParameters(parallelism=0).validate()

    def test_invalid_salt_length_rejected(self) -> None:
        with pytest.raises(InvalidKDFParametersError):
            KDFParameters(salt_length=32).validate()

    def test_invalid_hash_length_rejected(self) -> None:
        with pytest.raises(InvalidKDFParametersError):
            KDFParameters(hash_length=64).validate()


class TestKEKDerivation:
    """Test suite for derive_kek mathematical behavior and error handling."""

    @pytest.fixture
    def test_params(self) -> KDFParameters:
        return KDFParameters.fast_for_testing()

    @pytest.fixture
    def sample_salt(self) -> bytes:
        return b"\x01" * 16

    def test_output_is_exactly_32_bytes(
        self, test_params: KDFParameters, sample_salt: bytes
    ) -> None:
        kek = derive_kek("SecretPassword123!", sample_salt, test_params)
        assert isinstance(kek, bytes)
        assert len(kek) == 32

    def test_kdf_is_deterministic_for_identical_inputs(
        self, test_params: KDFParameters, sample_salt: bytes
    ) -> None:
        kek1 = derive_kek("SecretPassword123!", sample_salt, test_params)
        kek2 = derive_kek("SecretPassword123!", sample_salt, test_params)
        assert kek1 == kek2

    def test_different_passwords_produce_different_keys(
        self, test_params: KDFParameters, sample_salt: bytes
    ) -> None:
        kek1 = derive_kek("Password_Alpha", sample_salt, test_params)
        kek2 = derive_kek("Password_Beta", sample_salt, test_params)
        assert kek1 != kek2

    def test_different_salts_produce_different_keys(
        self, test_params: KDFParameters
    ) -> None:
        salt1 = b"\x01" * 16
        salt2 = b"\x02" * 16
        kek1 = derive_kek("ConsistentPassword", salt1, test_params)
        kek2 = derive_kek("ConsistentPassword", salt2, test_params)
        assert kek1 != kek2

    def test_parameter_changes_produce_different_keys(
        self, sample_salt: bytes
    ) -> None:
        p1 = KDFParameters(memory_cost=1024, time_cost=1, parallelism=1)
        p2 = KDFParameters(memory_cost=2048, time_cost=1, parallelism=1)
        kek1 = derive_kek("TestPassword", sample_salt, p1)
        kek2 = derive_kek("TestPassword", sample_salt, p2)
        assert kek1 != kek2

    def test_empty_password_rejected(
        self, test_params: KDFParameters, sample_salt: bytes
    ) -> None:
        with pytest.raises(InvalidPasswordInputError):
            derive_kek("", sample_salt, test_params)
        with pytest.raises(InvalidPasswordInputError):
            derive_kek(b"", sample_salt, test_params)

    def test_malformed_salt_length_rejected(
        self, test_params: KDFParameters
    ) -> None:
        with pytest.raises(InvalidSaltError):
            derive_kek("ValidPassword123!", b"short_salt", test_params)
        with pytest.raises(InvalidSaltError):
            derive_kek("ValidPassword123!", b"too_long_salt_longer_than_16_bytes!", test_params)

    def test_non_bytes_salt_rejected(
        self, test_params: KDFParameters
    ) -> None:
        with pytest.raises(InvalidSaltError):
            derive_kek("ValidPassword123!", "string_salt_not_bytes", test_params)  # type: ignore

    def test_production_parameters_run_successfully(self) -> None:
        """Verify that default production parameters (64 MiB, t=3, p=4) execute cleanly."""
        salt = generate_salt()
        kek = derive_kek("ProductionPasswordTest#2026", salt, KDFParameters.default())
        assert len(kek) == 32
