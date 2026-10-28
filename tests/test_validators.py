import pytest

from validators import (
    ValidationError,
    validate_chat_message,
    validate_guided_emotion,
    validate_password,
    validate_username,
    validate_video_language,
)


def test_username_validation():
    assert validate_username("tanuj_123") == "tanuj_123"
    with pytest.raises(ValidationError):
        validate_username("bad username")


def test_password_length_bounds():
    assert validate_password("correct-horse-battery") == "correct-horse-battery"
    with pytest.raises(ValidationError):
        validate_password("short")
    with pytest.raises(ValidationError):
        validate_password("x" * 1025)


def test_chat_message_limit_and_type():
    assert validate_chat_message("  hello  ") == "hello"
    with pytest.raises(ValidationError):
        validate_chat_message(["not", "text"])
    with pytest.raises(ValidationError):
        validate_chat_message("x" * 1001)


def test_guided_emotion_rejects_unhashable_payloads_cleanly():
    assert validate_guided_emotion("") is None
    assert validate_guided_emotion("stress") == "stress"
    with pytest.raises(ValidationError):
        validate_guided_emotion({"unexpected": "payload"})


def test_video_language_validation():
    assert validate_video_language(None) == "en"
    assert validate_video_language("en") == "en"
    assert validate_video_language("hi") == "hi"
    with pytest.raises(ValidationError):
        validate_video_language("fr")
