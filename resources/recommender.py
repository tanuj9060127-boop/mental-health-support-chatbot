"""
Resource recommendation and personalized video matching.

Existing article resources remain emotion-based for backward compatibility.
Video matching is problem/context/goal/intent driven and uses emotion only
as a supporting signal.
"""
import json
import logging
import re
from pathlib import Path
import config

logger = logging.getLogger("mh_chatbot.resources")

_RESOURCES = {}
_VIDEOS = []

def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("Could not load resource file %r: %s", path, e)
        return {}

_RESOURCES = _load_json(config.RESOURCE_FILE)
video_file = getattr(config, "VIDEO_RESOURCE_FILE",
                     str(Path(config.RESOURCE_FILE).with_name("videos.json")))
_video_data = _load_json(video_file)
if isinstance(_video_data, list):
    _VIDEOS = _video_data
elif isinstance(_video_data, dict):
    _VIDEOS = _video_data.get("videos", [])
else:
    _VIDEOS = []

def get_resources(emotion: str):
    """Legacy article/general-resource lookup, retained for compatibility."""
    try:
        candidates = _RESOURCES.get(emotion) or _RESOURCES.get("neutral") or []
        return [r for r in candidates if r.get("active", True)]
    except Exception as e:
        logger.warning("Resource lookup failed for emotion=%r: %s", emotion, e)
        return []

def _tokens(value):
    return set(re.findall(r"[a-z0-9_]+", str(value or "").lower()))

def _profile_tokens(profile):
    values = [
        profile.get("primary_problem"),
        profile.get("specific_issue"),
        profile.get("intent"),
        profile.get("emotion"),
    ]
    values += profile.get("contexts", []) or []
    values += profile.get("problem_tags", []) or []
    values += profile.get("goals", []) or []
    return _tokens(" ".join(map(str, values)))

def _video_tokens(video):
    values = [
        video.get("title"), video.get("description"), video.get("topic"),
        video.get("intent"), video.get("emotion"),
    ]
    for key in ("contexts", "problem_tags", "goals", "topics"):
        values += video.get(key, []) or []
    return _tokens(" ".join(map(str, values)))

def match_videos(profile, threshold=None, limit=3, exclude_ids=None):
    """
    Return only videos that meet the configured relevance threshold.

    Scoring is intentionally explainable:
      - problem overlap: strongest
      - context/goal/intent: strong
      - emotion: supporting signal
    It is a recommendation heuristic, not a clinical score.
    """
    if not isinstance(profile, dict):
        return []
    threshold = config.VIDEO_MATCH_THRESHOLD if threshold is None else threshold
    p = _profile_tokens(profile)
    results = []
    excluded = {str(value) for value in (exclude_ids or [])}

    for video in _VIDEOS:
        if not video.get("active", True) or video.get("resource_type") != "video":
            continue
        if str(video.get("id")) in excluded:
            continue

        v = _video_tokens(video)
        overlap = p & v
        if not overlap:
            continue

        specific_issue = str(profile.get("specific_issue") or "")
        problem_words = _tokens(" ".join(
            [str(profile.get("primary_problem") or "")] +
            [str(tag) for tag in (profile.get("problem_tags", []) or [])] +
            specific_issue.split()
        ))
        context_words = _tokens(" ".join(profile.get("contexts", []) or []))
        goal_words = _tokens(" ".join(profile.get("goals", []) or []))
        intent_words = _tokens(profile.get("intent"))
        emotion_words = _tokens(profile.get("emotion"))

        score = 0.0
        score += min(0.50, len(overlap & problem_words) * 0.12)
        score += min(0.25, len(overlap & context_words) * 0.08)
        score += min(0.15, len(overlap & goal_words) * 0.07)
        score += min(0.10, len(overlap & intent_words) * 0.05)
        score += min(0.08, len(overlap & emotion_words) * 0.04)

        # Small normalization bonus for broader overlap, capped.
        score += min(0.10, len(overlap) * 0.01)
        score = min(score, 1.0)

        if score >= threshold:
            item = dict(video)
            item["match_score"] = round(score, 3)
            results.append(item)

    results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return results[:limit]

def get_video_resources(
    profile,
    exclude_ids=None,
    limit=3,
):
    """
    Return personalized curated videos.

    exclude_ids can contain videos already shown to the user.
    """

    return match_videos(
        profile,
        limit=limit,
        exclude_ids=exclude_ids,
    )
