"""Tests for input validation and password strength estimation."""

import pytest

from app.core.validation import (
    estimate_password_strength,
    validate_login_id,
    validate_master_password,
)


class TestLoginIdValidation:
    """Test suite for Login ID validation rules."""

    @pytest.mark.parametrize(
        "valid_id",
        [
            "alice",
            "bob_123",
            "user.name",
            "developer-work",
            "security@example.com",
            "admin_user",  # contains 'admin' as substring but not exact match
            "a" * 64,      # maximum length boundary
        ],
    )
    def test_valid_login_ids_accepted(self, valid_id: str) -> None:
        is_valid, error = validate_login_id(valid_id)
        assert is_valid is True
        assert error == ""

    @pytest.mark.parametrize(
        "empty_or_whitespace",
        ["", "   ", "\t", "\n"],
    )
    def test_empty_or_whitespace_rejected(self, empty_or_whitespace: str) -> None:
        is_valid, error = validate_login_id(empty_or_whitespace)
        assert is_valid is False
        assert "cannot be empty" in error

    def test_short_login_id_rejected(self) -> None:
        is_valid, error = validate_login_id("ab")
        assert is_valid is False
        assert "at least 3 characters" in error

    def test_long_login_id_rejected(self) -> None:
        is_valid, error = validate_login_id("a" * 65)
        assert is_valid is False
        assert "cannot exceed 64 characters" in error

    @pytest.mark.parametrize(
        "invalid_chars",
        [
            "user name",     # space
            "user#name",     # hash
            "user$123",      # dollar
            "user/slash",    # slash
            "user\\bslash",  # backslash
            "user!alert",    # exclamation
        ],
    )
    def test_invalid_characters_rejected(self, invalid_chars: str) -> None:
        is_valid, error = validate_login_id(invalid_chars)
        assert is_valid is False
        assert "may only contain letters" in error

    @pytest.mark.parametrize(
        "prohibited",
        ["admin", "ADMIN", "root", "Root", "superuser", "null", "undefined"],
    )
    def test_reserved_login_ids_rejected(self, prohibited: str) -> None:
        is_valid, error = validate_login_id(prohibited)
        assert is_valid is False
        assert "reserved and cannot be used" in error


class TestMasterPasswordValidation:
    """Test suite for Master Password matching and length rules."""

    def test_matching_valid_passwords_accepted(self) -> None:
        is_valid, error = validate_master_password("CorrectHorseBattery123!", "CorrectHorseBattery123!")
        assert is_valid is True
        assert error == ""

    def test_empty_password_rejected(self) -> None:
        is_valid, error = validate_master_password("", "")
        assert is_valid is False
        assert "cannot be empty" in error

    def test_short_password_rejected(self) -> None:
        is_valid, error = validate_master_password("short", "short")
        assert is_valid is False
        assert "at least 8 characters" in error

    def test_mismatched_passwords_rejected(self) -> None:
        is_valid, error = validate_master_password("SecretPassword123!", "DifferentPassword123!")
        assert is_valid is False
        assert "do not match" in error


class TestPasswordStrengthEstimation:
    """Test suite for local advisory password strength estimation."""

    def test_empty_password(self) -> None:
        label, score = estimate_password_strength("")
        assert label == "Empty"
        assert score == 0

    def test_weak_password(self) -> None:
        label, score = estimate_password_strength("simple")
        assert label == "Weak"
        assert 0 < score < 40

    def test_medium_password(self) -> None:
        label, score = estimate_password_strength("password123")
        assert label == "Medium"
        assert 40 <= score < 70

    def test_strong_password(self) -> None:
        label, score = estimate_password_strength("Correct-Horse-Battery-Staple#2026")
        assert label in ("Strong", "Very Strong")
        assert score >= 70
