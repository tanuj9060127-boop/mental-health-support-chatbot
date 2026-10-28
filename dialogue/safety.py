"""
dialogue/safety.py

CONCEPT (Parts 18-19 - Safety Module):
------------------------------------------
This check runs on EVERY message, BEFORE emotion classification or guided
questioning (see dialogue/manager.py - it is checked first). If it fires,
the normal adaptive-questioning flow is skipped entirely and a fixed,
safety-oriented response is shown instead.

    User message
         v
    Safety screening  --------> if triggered: fixed safety response,
         v                       normal flow is skipped entirely
    (not triggered)
         v
    Normal conversation continues (emotion classification, etc.)

WHY KEYWORD MATCHING, NOT A "SMARTER" MODEL:
    A transparent, exhaustively-listable keyword check is easier to audit
    and test than a black-box classifier making a judgment call here -
    and this is the single highest-risk failure mode in the whole system,
    so auditability matters more than sophistication for a student project.

DOCUMENTED LIMITATIONS (Part 31, repeated here deliberately):
    - This is a basic safety net appropriate for a course project. It is
      NOT a clinically validated crisis-detection system and must never be
      described as one.
    - Keyword matching will miss indirect, coded, or non-English phrasing.
    - It cannot assess actual risk level - it only recognizes that a
      conversation may need to be redirected toward real human/professional
      support, and does so unconditionally when triggered.
    - This module does not attempt to diagnose the user in any way.

PRIVACY NOTE (Part 30): this function does not store anything beyond what
the normal message-logging flow already stores (the user's message text,
as with any other message). It does not create any additional
"flagged"/"risk" record - keeping a special sensitive-content table would
itself be a privacy risk without a clear, justified purpose in a course
project, per Part 18's "avoid unnecessarily storing sensitive safety-
related information".
"""

CRISIS_KEYWORDS = [
    "kill myself", "suicide", "end my life", "want to die", "self harm",
    "self-harm", "hurt myself", "no reason to live", "can't go on",
    "cant go on", "better off dead",
]

SAFETY_RESPONSE = (
    "It sounds like you might be going through something really difficult "
    "right now, and I want to make sure you get support beyond what I can "
    "offer. I'm a support chatbot, not a crisis service or a therapist, "
    "so I can't assess how serious this is - what I can do is point you "
    "toward people who can.\n\n"
    "If you are in immediate danger, please contact your local emergency "
    "number right now.\n\n"
    "If you're in the US, you can call or text 988 (the 988 Suicide & "
    "Crisis Lifeline) any time, day or night: https://988lifeline.org\n\n"
    "Outside the US, Find A Helpline lists free, confidential crisis lines "
    "by country: https://findahelpline.com\n\n"
    "Reaching out to a trusted person in your life right now - a friend, "
    "family member, or doctor - can also help. You don't have to go "
    "through this alone."
)


def is_crisis_message(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in CRISIS_KEYWORDS)
