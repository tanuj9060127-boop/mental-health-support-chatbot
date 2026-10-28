"""Text-to-speech helper for generated video narration.

The gTTS backend needs an internet connection. It receives only the generic,
controlled narration script, not the user's raw chat message. For sensitive
production use, replace this module with a privacy-reviewed or local TTS
provider.
"""

from pathlib import Path

LANGUAGE_CODES = {"en": "en", "hi": "hi"}


def synthesize_speech(text: str, output_path: str | Path, language: str = "en") -> str:
    if language not in LANGUAGE_CODES:
        raise ValueError("Video language must be 'en' or 'hi'.")
    clean_text = " ".join(str(text or "").split())
    if not clean_text:
        raise ValueError("Narration text cannot be empty.")

    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RuntimeError(
            "Voice narration requires gTTS. Install the project dependencies with `pip install -r requirements.txt`."
        ) from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        gTTS(text=clean_text, lang=LANGUAGE_CODES[language], slow=False).save(str(path))
    except Exception as exc:
        raise RuntimeError(
            "Could not generate voice narration. Check the internet connection and try again."
        ) from exc

    if not path.is_file() or path.stat().st_size < 256:
        raise RuntimeError("The speech service returned an empty audio file.")
    return str(path)
