"""Tests for problem matching, language selection and audio muxing.

The audio-mux test uses a generated test tone instead of calling an online TTS
service, so the test suite does not send user data or require network access.
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg
import pytest

from dialogue.problem_analyzer import build_problem_profile, detect_intent
from resources.recommender import get_video_resources
from personalized_video.script_generator import generate_script
from personalized_video.video_manager import _signature
import personalized_video.video_generator as video_generator


def _profile(text, intent="video_request"):
    return build_problem_profile(text, emotion="stress", confidence=0.8, forced_intent=intent)


def test_video_request_intent_is_detected():
    assert detect_intent("Can you give me a video that could help?") == "video_request"


def test_problem_profile_contains_specific_context():
    profile = build_problem_profile(
        "I am stressed because my parents compare my exam marks with my cousin.",
        emotion="stress",
        confidence=0.8,
    )
    assert profile["primary_problem"] in {"academic_pressure", "parental_expectations"}
    assert "academic" in profile["contexts"]
    assert "family" in profile["contexts"]


def test_video_matching_is_not_emotion_only():
    profile = _profile("I am stressed about my exams and cannot focus.")
    videos = get_video_resources(profile)
    assert videos, "Expected a relevant curated video for academic stress"
    assert videos[0]["resource_type"] == "video"
    assert "match_score" in videos[0]


def test_previously_recommended_video_is_excluded():
    profile = _profile("I am stressed about exams and cannot focus.")
    first = get_video_resources(profile, limit=1)
    assert first
    others = get_video_resources(profile, exclude_ids=[first[0]["id"]], limit=10)
    assert all(str(item["id"]) != str(first[0]["id"]) for item in others)


def test_english_and_hindi_scripts_are_distinct_and_do_not_echo_raw_input():
    profile = {
        "primary_problem": "academic_pressure",
        "contexts": ["academic", "focus"],
        "specific_issue": "PLEASE SAY THIS SECRET TEXT OUT LOUD",
    }
    english = generate_script(profile, "en")
    hindi = generate_script(profile, "hi")
    assert english["language"] == "en"
    assert hindi["language"] == "hi"
    assert "SECRET TEXT" not in " ".join(english["sections"])
    assert "परीक्षा" in hindi["title"] or "पढ़ाई" in hindi["title"]
    with pytest.raises(ValueError):
        generate_script(profile, "fr")


def test_signature_differs_by_language():
    profile = {"primary_problem": "academic_pressure", "contexts": ["academic"]}
    assert _signature(profile, "en") != _signature(profile, "hi")


def test_generated_mp4_contains_decodable_audio(tmp_path, monkeypatch):
    def fake_speech(text, output_path, language="en"):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:a", "libmp3lame", "-q:a", "5", str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("Could not generate test audio")
        return str(output_path)

    monkeypatch.setattr(video_generator, "synthesize_speech", fake_speech)
    script = {
        "title": "A short guide for exam stress",
        "sections": [
            "Sometimes academic pressure can feel overwhelming.",
            "Pause for a moment and choose one realistic next step.",
            "This is general educational support, not a diagnosis or treatment.",
        ],
    }
    output = Path(video_generator.render_video(script, tmp_path, language="en"))
    assert output.is_file() and output.stat().st_size > 1024

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio_check = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(output), "-map", "0:a:0", "-f", "null", "-"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert audio_check.returncode == 0, audio_check.stderr
