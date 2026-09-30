"""SecureVault — Input Validation & Password Strength Estimation.

Provides validation rules for Login ID and Master Password inputs,
along with local, advisory password strength estimation.
"""

from __future__ import annotations

import re

# Allowed characters for Login ID: alphanumeric, underscores, hyphens, periods, and @
LOGIN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.@-]{3,64}$")

# Disallowed keywords in Login ID
PROHIBITED_LOGIN_KEYWORDS = frozenset({
    "admin",
    "root",
    "superuser",
    "password",
    "null",
    "undefined",
})

MIN_PASSWORD_LENGTH = 8
RECOMMENDED_PASSWORD_LENGTH = 12


def validate_login_id(login_id: str) -> tuple[bool, str]:
    """Validate user-entered Login ID.

    Rules:
      - Cannot be empty or purely whitespace
      - Must be 3 to 64 characters in length
      - May contain letters, digits, '.', '_', '-', and '@'
      - Cannot match restricted system names

    Returns:
        tuple[bool, str]: (is_valid, error_message_or_empty)
    """
    trimmed = login_id.strip()
    if not trimmed:
        return False, "Login ID cannot be empty."

    if len(trimmed) < 3:
        return False, "Login ID must be at least 3 characters long."

    if len(trimmed) > 64:
        return False, "Login ID cannot exceed 64 characters."

    if not LOGIN_ID_PATTERN.match(trimmed):
        return False, "Login ID may only contain letters, numbers, '.', '_', '-', and '@'."

    if trimmed.lower() in PROHIBITED_LOGIN_KEYWORDS:
        return False, f"Login ID '{trimmed}' is reserved and cannot be used."

    return True, ""


def validate_master_password(password: str, confirm_password: str) -> tuple[bool, str]:
    """Validate master password and confirmation match.

    Rules:
      - Password cannot be empty
      - Must meet minimum length requirements
      - Confirmation must match identically

    Returns:
        tuple[bool, str]: (is_valid, error_message_or_empty)
    """
    if not password:
        return False, "Master password cannot be empty."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Master password must be at least {MIN_PASSWORD_LENGTH} characters."

    if password != confirm_password:
        return False, "Passwords do not match."

    return True, ""


def estimate_password_strength(password: str) -> tuple[str, int]:
    """Estimate password strength for advisory UI feedback.

    IMPORTANT: This is purely advisory feedback based on length and character
    variety. It does not provide cryptographic guarantees of entropy.
    No password data is transmitted externally.

    Returns:
        tuple[str, int]: (rating_label, percentage_score_0_to_100)
    """
    if not password:
        return "Empty", 0

    score = 0
    length = len(password)

    # Length scoring
    if length >= 8:
        score += 20
    if length >= 12:
        score += 20
    if length >= 16:
        score += 15

    # Character variety scoring
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))

    types_count = sum([has_lower, has_upper, has_digit, has_symbol])
    score += types_count * 10

    # Extra bonus for all 4 types
    if types_count == 4:
        score += 5

    score = min(max(score, 10), 100)

    if score < 40:
        return "Weak", score
    if score < 70:
        return "Medium", score
    if score < 90:
        return "Strong", score
    return "Very Strong", score
