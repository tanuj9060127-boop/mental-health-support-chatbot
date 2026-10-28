"""
tests/test_emotion_classifier.py

Part 32 - Testing: emotion classification, ambiguous input, negation.

Runs standalone (python tests/test_emotion_classifier.py) or under pytest.
Requires emotion/model.joblib to exist - run `python evaluate_model.py`
first if it doesn't.

IMPORTANT (Part 40 - no invented results): these tests check STRUCTURAL
correctness (a label from the known set, a confidence in [0,1], all
classes present in all_scores) for every case. For the "clear emotion"
cases, they assert the expected label - if you change/expand the training
dataset, an assertion here failing is a legitimate signal to look at the
model, not a bug in the test. For the negation cases, this test suite does
NOT assert a specific correct label - see the docstring on
test_negation_is_tested for why, and read the printed output.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emotion.classifier import EmotionClassifier

EXPECTED_LABELS = {"joy", "sadness", "anger", "fear", "stress", "confusion", "neutral"}

_clf = None


def get_classifier():
    global _clf
    if _clf is None:
        _clf = EmotionClassifier()
    return _clf


def _assert_valid_prediction(emotion, confidence, all_scores):
    assert emotion in EXPECTED_LABELS, f"Unexpected label: {emotion}"
    assert 0.0 <= confidence <= 1.0, f"Confidence out of range: {confidence}"
    assert set(all_scores.keys()) == EXPECTED_LABELS
    assert abs(sum(all_scores.values()) - 1.0) < 1e-6, "Probabilities should sum to 1"


def test_clear_joy():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I got selected for the competition and I am thrilled")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "joy"


def test_clear_sadness():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I feel very lonely and I have been crying a lot lately")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "sadness"


def test_clear_anger():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I am furious, this whole situation is making my blood boil")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "anger"


def test_clear_fear():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I am terrified and anxious about the exam results tomorrow")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "fear"


def test_clear_stress():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I am overwhelmed, there is just too much on my plate right now")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "stress"


def test_clear_confusion():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("I don't know how I feel, it's hard to explain")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "confusion"


def test_clear_neutral():
    clf = get_classifier()
    emotion, confidence, scores = clf.predict("Today was a normal day, nothing special happened")
    _assert_valid_prediction(emotion, confidence, scores)
    assert emotion == "neutral"


def test_ambiguous_inputs_are_structurally_valid():
    """Part 13: these short, low-information inputs must not crash the
    classifier and must return a valid probability distribution. Whatever
    label they get, the DIALOGUE MANAGER (not this test) is responsible for
    treating "confusion" or low confidence as a signal to ask a guided
    question rather than presenting the label as a settled fact - see
    tests/test_dialogue_manager.py."""
    clf = get_classifier()
    for text in ["I don't know.", "I'm fine.", "Nothing.", "Whatever."]:
        emotion, confidence, scores = clf.predict(text)
        _assert_valid_prediction(emotion, confidence, scores)


def test_negation_is_tested():
    """
    Part 12: HONEST RESULT, NOT A PASS/FAIL ASSERTION.

    We deliberately do NOT assert that these come out "correct", because
    with this dataset size they often do not (see emotion/evaluation_report.txt
    and README.md "Known limitation: negation"). Asserting a specific label
    here would either be a false claim of success or a test that blocks
    legitimate dataset changes. Instead this test documents the ACTUAL
    behavior by printing it, and only checks the prediction pipeline
    doesn't crash on negated input.
    """
    clf = get_classifier()
    cases = ["I am not happy.", "I am not angry.", "I'm not worried.", "I don't feel sad."]
    print("\nNegation probe results (see README.md for discussion):")
    for text in cases:
        emotion, confidence, scores = clf.predict(text)
        _assert_valid_prediction(emotion, confidence, scores)
        print(f"  {text!r:25} -> {emotion} ({confidence:.2f})")


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
