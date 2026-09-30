"""Tests for initialization service, first-run detection, and state persistence."""

import json
from pathlib import Path
import pytest

from app.core.config import AppConfig
from app.core.exceptions import ConfigurationError
from app.services.initialization import (
    INIT_STATE_FILENAME,
    InitializationService,
    SessionState,
)


@pytest.fixture
def temp_init_service(tmp_path: Path) -> InitializationService:
    """Fixture providing an InitializationService bound to an isolated temporary directory."""
    config = AppConfig(data_dir=tmp_path)
    return InitializationService(config)


def test_initial_state_is_uninitialized(temp_init_service: InitializationService) -> None:
    """Verify that a fresh environment is identified as uninitialized."""
    assert temp_init_service.is_initialized() is False
    assert temp_init_service.get_session_state() == SessionState.UNINITIALIZED
    assert temp_init_service.get_login_id() is None


def test_successful_initialization(temp_init_service: InitializationService) -> None:
    """Verify initialization records state and transitions to LOCKED."""
    temp_init_service.initialize("alice_dev")

    assert temp_init_service.is_initialized() is True
    assert temp_init_service.get_session_state() == SessionState.LOCKED
    assert temp_init_service.get_login_id() == "alice_dev"


def test_initialization_file_content_is_strictly_non_sensitive(
    temp_init_service: InitializationService,
) -> None:
    """Verify that init_state.json contains only safe metadata and no secrets."""
    temp_init_service.initialize("security_user")

    init_file = temp_init_service.init_file_path
    assert init_file.exists()

    with open(init_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Allowed non-sensitive fields
    assert set(data.keys()) == {"initialized", "login_id", "created_at", "format_version"}
    assert data["initialized"] is True
    assert data["login_id"] == "security_user"
    assert data["format_version"] == 1

    # Security verification: no password or cryptographic keys present
    forbidden_terms = ["password", "hash", "secret", "key", "kek", "dek", "token"]
    raw_content = init_file.read_text(encoding="utf-8").lower()
    for term in forbidden_terms:
        assert term not in raw_content, f"Forbidden term '{term}' found in initialization state file!"


def test_initialize_with_invalid_login_id_raises_error(
    temp_init_service: InitializationService,
) -> None:
    """Verify that attempting to initialize with invalid Login ID fails and does not create state."""
    with pytest.raises(ConfigurationError):
        temp_init_service.initialize("")

    assert temp_init_service.is_initialized() is False
    assert not temp_init_service.init_file_path.exists()


def test_reset_initialization_state(temp_init_service: InitializationService) -> None:
    """Verify that reset() cleanly deletes the initialization marker."""
    temp_init_service.initialize("bob_tester")
    assert temp_init_service.is_initialized() is True

    temp_init_service.reset()
    assert temp_init_service.is_initialized() is False
    assert temp_init_service.get_session_state() == SessionState.UNINITIALIZED
    assert not temp_init_service.init_file_path.exists()
