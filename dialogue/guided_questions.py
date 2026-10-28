"""
dialogue/guided_questions.py

CONCEPT (Section 7 - Guided Emotional Input):
----------------------------------------------
When the classifier isn't confident, instead of guessing we hand the user
a short multiple-choice menu. This is deliberately simple: tapping a button
is easier than writing a sentence for someone who is already struggling to
put feelings into words.

Each guided option maps directly onto one of our 7 emotion labels. A
button click is recorded by the dialogue manager as
classification_method = "user_selected" with model_confidence = NULL
(Part 7 fix) - it is a user's own answer, not a model prediction, so it
must never be stored as if the model were "100% confident".

If the user picks "Not sure", we don't loop back to the same question —
that would frustrate them (Section 8: "short enough that users do not
become frustrated"). Instead we ask ONE simple, open follow-up question,
then fall back to a general supportive/neutral response either way. This
gives the adaptive loop a hard stop after at most 2 extra questions.
"""

PRIMARY_OPTIONS = [
    {"label": "Calm / Okay", "emotion": "neutral"},
    {"label": "Worried", "emotion": "fear"},
    {"label": "Sad", "emotion": "sadness"},
    {"label": "Angry", "emotion": "anger"},
    {"label": "Stressed", "emotion": "stress"},
    {"label": "Not sure", "emotion": None},  # triggers the fallback question
]

FALLBACK_QUESTION = (
    "That's okay, you don't have to have a clear label for it. "
    "Would you like to tell me a bit about what's been on your mind, "
    "or has something specific been bothering you recently?"
)

GUIDED_PROMPT = "I'm not fully sure how you're feeling from that. Which feels closest to your current experience?"
