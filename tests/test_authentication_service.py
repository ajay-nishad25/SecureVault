"""Tests for Master AuthenticationService and session KEK lifecycle."""

import logging
import pytest

from app.core.exceptions import AuthenticationError
from app.crypto.kdf import KDFParameters, generate_salt
from app.services.authentication import AuthenticationResult, AuthenticationService


@pytest.fixture
def fast_auth_service() -> AuthenticationService:
    """Fixture providing AuthenticationService configured with fast test parameters."""
    return AuthenticationService(kdf_parameters=KDFParameters.fast_for_testing())


def test_auth_service_initial_state(fast_auth_service: AuthenticationService) -> None:
    """Verify service initial state has no active key."""
    assert fast_auth_service.has_active_kek() is False
    assert fast_auth_service.get_active_kek() is None


def test_authenticate_empty_password_rejected(
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify that submitting an empty password fails without key derivation."""
    result = fast_auth_service.authenticate("")
    assert result.success is False
    assert result.kek is None
    assert "cannot be empty" in str(result.error)
    assert fast_auth_service.has_active_kek() is False


def test_authenticate_successful_derivation(
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify successful password authentication derives and holds 32-byte KEK."""
    salt = generate_salt()
    result = fast_auth_service.authenticate("CorrectHorseBattery2026!", salt=salt)

    assert result.success is True
    assert isinstance(result.kek, bytes)
    assert len(result.kek) == 32
    assert fast_auth_service.has_active_kek() is True
    assert fast_auth_service.get_active_kek() == result.kek


def test_clear_session_purges_kek(
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify that clear_session() zeroes and purges the active KEK buffer."""
    fast_auth_service.authenticate("SessionPassword#1")
    assert fast_auth_service.has_active_kek() is True

    fast_auth_service.clear_session()
    assert fast_auth_service.has_active_kek() is False
    assert fast_auth_service.get_active_kek() is None


def test_derive_key_direct_api(
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify derive_key returns KEK directly."""
    salt = generate_salt()
    kek = fast_auth_service.derive_key("DirectPassword", salt)
    assert isinstance(kek, bytes)
    assert len(kek) == 32


def test_derive_key_invalid_input_raises_authentication_error(
    fast_auth_service: AuthenticationService,
) -> None:
    """Verify that domain exceptions are wrapped into AuthenticationError."""
    with pytest.raises(AuthenticationError):
        fast_auth_service.derive_key("", b"0" * 16)

    with pytest.raises(AuthenticationError):
        fast_auth_service.derive_key("ValidPass", b"short_salt")


def test_password_and_kek_are_never_logged(
    fast_auth_service: AuthenticationService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify that sensitive master passwords and KEK bytes are never recorded in logs."""
    test_password = "SuperSecretMasterPassword!#98765"
    salt = generate_salt()

    with caplog.at_level(logging.DEBUG):
        result = fast_auth_service.authenticate(test_password, salt=salt)

    assert result.success is True
    assert result.kek is not None

    full_log_text = caplog.text
    # Master password must not appear anywhere in logs
    assert test_password not in full_log_text
    # Raw KEK hex representation must not appear anywhere in logs
    assert result.kek.hex() not in full_log_text
