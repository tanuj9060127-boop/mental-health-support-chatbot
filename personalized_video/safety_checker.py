"""Lightweight checks for generated educational/supportive scripts.

This is a defensive phrase check, not a comprehensive clinical safety system.
"""

DISALLOWED = (
    "you have depression",
    "you have an anxiety disorder",
    "you have anxiety disorder",
    "this will cure you",
    "guaranteed cure",
    "stop your medication",
    "stop taking your medication",
    "you do not need professional help",
    "you don't need professional help",
)


def validate_script(script):
    lowered = (script or "").casefold()
    problems = [phrase for phrase in DISALLOWED if phrase in lowered]
    return {"safe": not problems, "problems": problems}
