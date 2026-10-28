"""
validators.py

CONCEPT (Part 26 - Input Validation):
----------------------------------------
Every value that comes from the browser is untrusted until checked. This
module centralizes those checks so routes/chat_routes.py and
routes/auth_routes.py don't each re-implement (or forget) validation.

WHAT THIS DOES NOT DO: SQL injection protection is handled separately, by
always using parameterized queries in db.py (never string-formatted SQL).
This module only checks shape/length/character constraints on input
BEFORE it reaches the database or the classifier.
"""

import re
import config

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class ValidationError(Exception):
    """Raised with a user-safe message describing why input was rejected."""
    pass


def validate_username(username: str) -> str:
    if not username or not isinstance(username, str):
        raise ValidationError("Username is required.")
    username = username.strip()
    if not (config.MIN_USERNAME_LENGTH <= len(username) <= config.MAX_USERNAME_LENGTH):
        raise ValidationError(
            f"Username must be between {config.MIN_USERNAME_LENGTH} and "
            f"{config.MAX_USERNAME_LENGTH} characters."
        )
    if not USERNAME_PATTERN.match(username):
        raise ValidationError("Username may only contain letters, numbers, and underscores.")
    return username


def validate_password(password: str) -> str:
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required.")
    if len(password) < config.MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.")
    if len(password) > config.MAX_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be no more than {config.MAX_PASSWORD_LENGTH} characters.")
    return password


def validate_chat_message(message: str) -> str:
    """Empty string is allowed (guided-option clicks send no free text)."""
    if message is None:
        return ""
    if not isinstance(message, str):
        raise ValidationError("Invalid message format.")
    message = message.strip()
    if len(message) > config.MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message is too long (max {config.MAX_MESSAGE_LENGTH} characters).")
    return message


def validate_guided_emotion(value):
    """Validate an emotion string, an empty Not-sure value, or None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("Invalid guided emotion selection.")
    if value == "":
        return None  # "Not sure" - internally represented as None downstream
    if value not in config.ALLOWED_GUIDED_EMOTIONS:
        raise ValidationError("Invalid guided emotion selection.")
    return value


def validate_video_language(value) -> str:
    """Return the selected generated-video narration language (English/Hindi)."""
    if value in (None, ""):
        return "en"
    if not isinstance(value, str) or value not in config.ALLOWED_VIDEO_LANGUAGES:
        raise ValidationError("Video language must be English or Hindi.")
    return value
