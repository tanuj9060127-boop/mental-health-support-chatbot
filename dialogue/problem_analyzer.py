"""
dialogue/problem_analyzer.py

Extracts a lightweight, explainable problem profile from the current message
and recent conversation. This is intentionally not a diagnostic system.
It identifies conversation context and resource intent for personalization.
"""

import re

INTENT_PATTERNS = {
    "video_request": [
        r"\bvideo\b", r"\bwatch\b", r"\bsomething to watch\b",
        r"\bshow me\b.*\bvideo\b",
    ],
    "article_request": [r"\barticle\b", r"\bread\b.*\babout\b"],
    "exercise_request": [r"\bexercise\b", r"\bactivity\b", r"\bpractice\b"],
    "resource_request": [r"\bresource\b", r"\blink\b", r"\bhelpful material\b"],
    "advice_request": [r"\bwhat can i do\b", r"\bhow can i\b", r"\bwhat should i do\b",
                       r"\bhow do i\b", r"\badvice\b", r"\bsuggest\b"],
    "venting": [r"\bjust want to talk\b", r"\bneed to vent\b", r"\bvent\b"],
}

CONTEXT_TAGS = {
    "academic": ["exam", "exams", "test", "tests", "assignment", "assignments",
                 "grades", "marks", "college", "university", "study", "studying",
                 "class", "course", "professor", "teacher"],
    "family": ["parent", "parents", "mother", "father", "family", "cousin", "siblings"],
    "friendship": ["friend", "friendship", "roommate", "classmate", "best friend"],
    "work": ["job", "work", "boss", "office", "internship", "coworker", "colleague"],
    "relationships": ["relationship", "partner", "breakup", "dating"],
    "social": ["lonely", "alone", "social", "people", "friends"],
    "sleep": ["sleep", "insomnia", "sleeping", "awake", "tired"],
    "focus": ["focus", "concentrate", "concentration", "distracted", "procrastinate"],
}

PROBLEM_TAGS = {
    "academic_pressure": ["exam pressure", "academic pressure", "study pressure",
                           "grades", "marks", "failing", "fail", "workload"],
    "parental_expectations": ["parents", "parent", "comparison", "compared", "cousin",
                              "expectations", "pressure from my parents"],
    "friend_conflict": ["argument", "fight", "conflict", "not talking", "fell out",
                        "roommate", "friend"],
    "loneliness": ["lonely", "alone", "isolated", "no one to talk"],
    "concentration": ["concentrate", "focus", "distracted", "procrastinating"],
    "sleep_difficulty": ["can't sleep", "cannot sleep", "insomnia", "sleeping badly"],
    "work_pressure": ["workload", "deadline", "boss", "job pressure", "office"],
}

GOAL_PATTERNS = {
    "coping": ["cope", "manage", "deal with", "handle", "reduce", "relieve"],
    "communication": ["talk to", "explain", "communicate", "tell my parents",
                      "talk with", "conversation"],
    "focus": ["focus", "concentrate", "study better"],
    "understanding": ["why", "understand", "what is happening"],
}

def _joined_text(message, history=None):
    parts = []
    if history:
        for item in history:
            if isinstance(item, dict) and item.get("sender") == "user":
                parts.append(str(item.get("message", "")))
    parts.append(message or "")
    return " ".join(parts).strip()

def detect_intent(message, history=None):
    text = _joined_text(message, history).lower()
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            return intent
    return "conversation"

def _matches(text, mapping):
    found = []
    for tag, words in mapping.items():
        if any(w in text for w in words):
            found.append(tag)
    return found

def build_problem_profile(message, emotion=None, confidence=None, history=None,
                           forced_intent=None):
    text = _joined_text(message, history)
    lowered = text.lower()

    contexts = _matches(lowered, CONTEXT_TAGS)
    problems = _matches(lowered, PROBLEM_TAGS)
    goals = _matches(lowered, GOAL_PATTERNS)

    intent = forced_intent or detect_intent(message, history)

    # Prefer a concrete problem label over an emotion-only label.
    if problems:
        primary_problem = problems[0]
    elif contexts:
        primary_problem = f"{contexts[0]}_related_concern"
    else:
        primary_problem = "general_wellbeing_concern"

    # Keep the raw current message as the specific issue; do not invent facts.
    specific_issue = (message or "").strip()[:1000]

    return {
        "emotion": emotion,
        "emotion_confidence": confidence,
        "intent": intent,
        "contexts": contexts,
        "problem_tags": problems,
        "primary_problem": primary_problem,
        "goals": goals,
        "specific_issue": specific_issue,
    }
