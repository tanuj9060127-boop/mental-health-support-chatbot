"""
tests/test_dialogue_manager.py

Part 32 - Testing: adaptive dialogue (low confidence -> guided question ->
user selects -> supportive response), "Not sure" flow, follow-up cap,
and user correction (Part 16).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dialogue.manager import DialogueManager

dm = DialogueManager()


def test_guided_click_is_user_selected_not_model_confidence():
    """Part 7 fix: this is the single most important regression test in
    the whole suite - a guided-menu click must NEVER be recorded as
    model confidence = 1.0."""
    state = dm.new_state()
    result = dm.handle_message("", state, guided_emotion="sadness")
    assert result["classification_method"] == "user_selected"
    assert result["model_confidence"] is None
    assert result["emotion"] == "sadness"


def test_low_confidence_or_confusion_triggers_guided_menu():
    state = dm.new_state()
    result = dm.handle_message("I don't know.", state)
    assert result["type"] == "clarify"
    assert result["guided_options"] is not None
    assert "Not sure" in result["guided_options"]


def test_not_sure_asks_a_different_question_not_the_same_one():
    state = dm.new_state()
    r1 = dm.handle_message("meh", state)
    assert r1["type"] == "clarify"
    first_question = r1["reply"]

    r2 = dm.handle_message("", r1["state"], guided_emotion=None)  # "Not sure" clicked
    assert r2["type"] == "clarify"
    second_question = r2["reply"]
    assert second_question != first_question, "Must not repeat the exact same question"


def test_follow_up_questions_are_capped():
    """Part 15: after MAX_FOLLOW_UP_QUESTIONS, the bot must respond
    instead of asking again, even with continued low-confidence input."""
    import config
    state = dm.new_state()
    r = dm.handle_message("meh", state)  # follow-up #1 (guided menu)
    assert r["type"] == "clarify"

    r = dm.handle_message("", r["state"], guided_emotion=None)  # follow-up #2 ("Not sure" -> fallback Q)
    assert r["type"] == "clarify"
    assert r["state"]["follow_up_count"] <= config.MAX_FOLLOW_UP_QUESTIONS

    # Any further low-information input must now get a final response,
    # not a third guided question.
    r = dm.handle_message("still not sure honestly", r["state"])
    assert r["type"] == "response", "Follow-up budget must be enforced - bot must respond, not ask again"


def test_full_adaptive_flow_low_confidence_to_supportive_response():
    """Low confidence -> guided choice -> reason -> detail -> response."""
    state = dm.new_state()
    r1 = dm.handle_message("I don't know.", state)
    assert r1["type"] == "clarify"
    assert r1["guided_options"] is not None

    r2 = dm.handle_message("", r1["state"], guided_emotion="stress")
    assert r2["type"] == "clarify"
    assert r2["emotion"] == "stress"
    assert r2["model_confidence"] is None
    assert r2["state"]["awaiting_reason"] is True

    r3 = dm.handle_message("I am stressed about exams.", r2["state"])
    assert r3["type"] == "clarify"
    assert r3["state"]["awaiting_follow_up"] is True

    r4 = dm.handle_message("I have too much to study and cannot focus.", r3["state"])
    assert r4["type"] == "response"
    assert r4["emotion"] == "stress"
    assert len(r4["reply"]) > 0
    assert "resources" in r4


def test_user_correction_uses_corrected_emotion():
    """Part 16: chatbot said 'worried' (fear), user says 'actually angry'."""
    correction = dm.correct(predicted_emotion="fear", corrected_emotion="anger")
    assert correction["emotion"] == "anger"
    assert correction["classification_method"] == "user_selected"
    assert correction["model_confidence"] is None


def test_safety_message_short_circuits_everything_else():
    state = dm.new_state()
    result = dm.handle_message("I want to end my life", state)
    assert result["type"] == "safety"
    assert result["guided_options"] is None
    assert result["emotion"] is None
    # Crisis resources must be present and real (not placeholders)
    assert "988lifeline.org" in result["reply"] or "findahelpline.com" in result["reply"]


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


def test_user_can_type_instead_of_clicking_guided_menu():
    state = dm.new_state()
    first = dm.handle_message("I don't know.", state)
    assert first["state"]["awaiting_guided_choice"] is True
    next_result = dm.handle_message("I am stressed about an exam tomorrow.", first["state"])
    assert next_result["type"] in {"clarify", "response"}
    assert next_result["reply"]


def test_raw_user_text_is_not_saved_in_client_dialogue_state():
    result = dm._final_response(
        "stress", None, "user_selected",
        message="RAW_PRIVATE_TEXT: my exact personal situation",
        forced_intent="conversation",
    )
    assert "RAW_PRIVATE_TEXT" not in repr(result["state"])
    assert "my exact personal situation" not in repr(result["state"])


def test_follow_up_rebuilds_reason_from_persisted_history():
    r1 = dm.handle_message("I don't know.", dm.new_state())
    r2 = dm.handle_message("", r1["state"], guided_emotion="stress")
    r3 = dm.handle_message("My family compares my exam marks.", r2["state"])
    assert r3["state"]["awaiting_follow_up"] is True
    assert "reason_text" not in r3["state"]

    history = [
        {"sender": "user", "message": "I don't know."},
        {"sender": "bot", "message": "What is on your mind?"},
        {"sender": "user", "message": "My family compares my exam marks."},
        {"sender": "bot", "message": "Tell me more."},
    ]
    r4 = dm.handle_message("I cannot focus while studying.", r3["state"], history=history)
    assert r4["type"] == "response"
    assert "My family compares my exam marks" in r4["problem_profile"]["specific_issue"]
    assert "I cannot focus while studying" in r4["problem_profile"]["specific_issue"]
