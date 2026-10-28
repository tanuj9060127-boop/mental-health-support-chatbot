"""
tests/test_safety.py

Part 32 - Testing: safety module, using predefined SAFE test cases only
(no dangerous or graphic examples, as instructed).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dialogue.safety import is_crisis_message, SAFETY_RESPONSE


def test_known_crisis_phrases_are_detected():
    cases = [
        "I want to end my life",
        "sometimes I think about suicide",
        "I just want to hurt myself",
    ]
    for text in cases:
        assert is_crisis_message(text) is True, f"Expected crisis detection for: {text!r}"


def test_ordinary_messages_are_not_flagged():
    cases = [
        "I had a great day today",
        "I am a bit stressed about exams",
        "I feel angry about the traffic this morning",
        "",
        None,
    ]
    for text in cases:
        assert is_crisis_message(text) is False, f"False positive on: {text!r}"


def test_safety_response_contains_real_resources_not_placeholders():
    assert "example.org" not in SAFETY_RESPONSE
    assert ("988" in SAFETY_RESPONSE) or ("findahelpline" in SAFETY_RESPONSE)


def test_safety_response_does_not_diagnose_or_claim_therapist_role():
    lowered = SAFETY_RESPONSE.lower()
    assert "you are depressed" not in lowered
    assert "i am a therapist" not in lowered
    assert "not a crisis service" in lowered or "not a therapist" in lowered


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__} - {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
