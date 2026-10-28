"""
Dialogue manager.

Decision layer for adaptive conversation plus personalized resource/video
recommendation.

Emotion remains part of the conversation state, but resources are selected
using the user's problem, context, goals, intent, and emotion.

Curated video recommendations are tracked so previously recommended videos
can be excluded from future recommendations.
"""

import logging

import config
import db

from emotion.classifier import EmotionClassifier
from resources.recommender import get_resources, get_video_resources
from dialogue.problem_analyzer import build_problem_profile
from dialogue.safety import is_crisis_message, SAFETY_RESPONSE
from dialogue import guided_questions as gq


logger = logging.getLogger("mh_chatbot.dialogue")


SUPPORTIVE_TEMPLATES = {
    "joy": (
        "That's wonderful to hear! It sounds like you may be feeling happy "
        "about this. Would you like to talk about what's made you feel this way?"
    ),
    "sadness": (
        "It sounds like you may be feeling sad or low right now. "
        "I'm here to listen if you'd like to share more - and if that's "
        "not quite right, feel free to tell me."
    ),
    "anger": (
        "It sounds like you may be feeling frustrated or angry about something. "
        "Do you want to talk through what triggered it? Let me know if that's "
        "not quite it."
    ),
    "fear": (
        "It sounds like you may be feeling worried about this. "
        "Would you like to talk about what's on your mind?"
    ),
    "stress": (
        "It sounds like a lot may be piling up for you right now. "
        "Would it help to talk about what's taking up the most space?"
    ),
    "confusion": (
        "It's completely okay not to have a clear word for how you feel. "
        "Do you want to describe what's been happening lately?"
    ),
    "neutral": (
        "Thanks for sharing that. Is there anything in particular "
        "you'd like to talk through today?"
    ),
}


CORRECTION_ACKNOWLEDGEMENT = (
    "Thanks for letting me know - I appreciate the correction."
)


_classifier = EmotionClassifier()


class DialogueManager:

    # -----------------------------------------------------------------
    # Conversation state
    # -----------------------------------------------------------------

    def new_state(self):
        return {
            "awaiting_guided_choice": False,
            "awaiting_fallback_answer": False,
            "awaiting_reason": False,
            "awaiting_follow_up": False,
            "follow_up_count": 0,
            "last_message_id": None,
            "pending_intent": None,
            "selected_emotion": None,
            "last_profile": None,
        }

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _merge_profiles(previous_profile, current_profile):
        """
        Keep useful problem context from the previous turn when the current
        message is only a resource request such as:
        "Can you recommend a video?"

        The current profile still supplies the current intent and any new
        information. Previous problem/context fields are retained when the
        current request does not provide them.
        """
        if not previous_profile:
            return current_profile

        if not current_profile:
            return dict(previous_profile)

        merged = dict(current_profile)

        list_fields = ("contexts", "problem_tags", "goals")

        for field in list_fields:
            previous_values = previous_profile.get(field) or []
            current_values = merged.get(field) or []

            combined = []
            for value in previous_values + current_values:
                if value not in combined:
                    combined.append(value)

            merged[field] = combined

        for field in ("primary_problem", "specific_issue"):
            current_value = merged.get(field)
            previous_value = previous_profile.get(field)

            if not current_value and previous_value:
                merged[field] = previous_value

        # The resource request must remain the current intent.
        if current_profile.get("intent"):
            merged["intent"] = current_profile["intent"]

        # Keep the remembered emotion when the current profile has no emotion.
        if not merged.get("emotion") and previous_profile.get("emotion"):
            merged["emotion"] = previous_profile["emotion"]

        return merged

    def _state_after_response(self, emotion, profile):
        """
        Persist the context needed for the next user turn.
        """
        state = self.new_state()
        state["selected_emotion"] = emotion
        # Flask's default session is signed, not encrypted. Never place raw
        # user text in it; keep only the small, structured profile fields.
        state["last_profile"] = {
            key: profile.get(key)
            for key in (
                "emotion", "emotion_confidence", "intent", "contexts",
                "problem_tags", "primary_problem", "goals",
            )
        } if profile else None
        return state

    # -----------------------------------------------------------------
    # Main message handler
    # -----------------------------------------------------------------

    def handle_message(
        self,
        message: str,
        state: dict,
        guided_emotion: str = None,
        history=None,
        conversation_id=None,
        user_id=None,
        video_language="en",
    ):
        state = state or self.new_state()

        # -------------------------------------------------------------
        # Safety check must happen before normal classification.
        # -------------------------------------------------------------

        if message and is_crisis_message(message):
            return {
                "type": "safety",
                "reply": SAFETY_RESPONSE,
                "emotion": None,
                "model_confidence": None,
                "classification_method": None,
                "resources": [],
                "guided_options": None,
                "correctable": False,
                "problem_profile": None,
                "state": self.new_state(),
            }

        # -------------------------------------------------------------
        # Guided emotion selection
        # -------------------------------------------------------------

        was_awaiting_guided = state.get("awaiting_guided_choice")

        if guided_emotion is not None or (was_awaiting_guided and not (message or "").strip()):

            # ---------------------------------------------------------
            # User selected a concrete emotion.
            # ---------------------------------------------------------

            if guided_emotion:
                new_state = dict(state)

                new_state["awaiting_guided_choice"] = False
                new_state["awaiting_fallback_answer"] = False
                new_state["awaiting_reason"] = True
                new_state["awaiting_follow_up"] = False
                new_state["selected_emotion"] = guided_emotion

                reason_prompts = {
                    "neutral": (
                        "Thanks for sharing. What's been on your mind recently?"
                    ),
                    "fear": (
                        "It sounds like you may be feeling worried. "
                        "What's making you feel worried?"
                    ),
                    "sadness": (
                        "It sounds like you may be feeling sad. "
                        "What's been weighing on your mind?"
                    ),
                    "anger": (
                        "It sounds like you may be feeling frustrated or angry. "
                        "What happened?"
                    ),
                    "stress": (
                        "It sounds like you may be feeling stressed. "
                        "What's causing you the most stress right now?"
                    ),
                    "joy": (
                        "It sounds like you may be feeling happy. "
                        "What's been making you feel this way?"
                    ),
                    "confusion": (
                        "It's okay if you're not sure how to describe it. "
                        "What's been confusing or difficult lately?"
                    ),
                }

                return {
                    "type": "clarify",
                    "reply": reason_prompts.get(
                        guided_emotion,
                        reason_prompts["neutral"],
                    ),
                    "emotion": guided_emotion,
                    "model_confidence": None,
                    "classification_method": "user_selected",
                    "resources": [],
                    "guided_options": None,
                    "correctable": False,
                    "problem_profile": None,
                    "state": new_state,
                }

            # ---------------------------------------------------------
            # User selected "Not sure".
            # ---------------------------------------------------------

            if was_awaiting_guided:
                new_state = dict(state)

                new_state["awaiting_guided_choice"] = False
                new_state["awaiting_fallback_answer"] = True
                new_state["follow_up_count"] = (
                    state.get("follow_up_count", 0) + 1
                )

                return {
                    "type": "clarify",
                    "reply": gq.FALLBACK_QUESTION,
                    "emotion": None,
                    "model_confidence": None,
                    "classification_method": None,
                    "resources": [],
                    "guided_options": None,
                    "correctable": False,
                    "problem_profile": None,
                    "state": new_state,
                }

        # -------------------------------------------------------------
        # Answer to fallback question.
        # -------------------------------------------------------------

        if state.get("awaiting_fallback_answer"):
            emotion, confidence, all_scores = _classifier.predict(message)
            emotion = emotion or "neutral"

            return self._final_response(
                emotion,
                confidence,
                "model",
                all_scores=all_scores,
                message=message,
                history=history,
                forced_intent=state.get("pending_intent"),
                conversation_id=conversation_id,
                user_id=user_id,
                video_language=video_language,
            )

        # -------------------------------------------------------------
        # Answer to guided emotion reason question.
        if state.get("awaiting_reason"):
            selected_emotion = state.get("selected_emotion") or "neutral"

            new_state = dict(state)
            new_state["awaiting_reason"] = False
            new_state["awaiting_follow_up"] = True
            # The reason text is retrieved from the persisted conversation
            # history on the next turn rather than stored in the client cookie.
            new_state.pop("reason_text", None)

            return {
                "type": "clarify",
                "reply": (
                    "Thanks for explaining. It sounds like the main issue is: "
                    f"{message.strip()}. "
                    "Could you tell me a little more about what makes this difficult?"
                ),
                "emotion": selected_emotion,
                "model_confidence": None,
                "classification_method": "user_selected",
                "resources": [],
                "guided_options": None,
                "correctable": False,
                "problem_profile": None,
                "state": new_state,
            }

        # Answer to follow-up question.
        if state.get("awaiting_follow_up"):
            selected_emotion = state.get("selected_emotion") or "neutral"
            reason_text = ""
            if history:
                for item in reversed(history):
                    if isinstance(item, dict) and item.get("sender") == "user":
                        previous_text = str(item.get("message") or "").strip()
                        if previous_text and not previous_text.startswith("[guided option:"):
                            reason_text = previous_text
                            break
            current_text = (message or "").strip()
            combined_message = " ".join(part for part in (reason_text, current_text) if part)

            profile = build_problem_profile(
                combined_message,
                emotion=selected_emotion,
                confidence=None,
                history=history,
            )

            result = self._final_response(
                selected_emotion,
                model_confidence=None,
                classification_method="user_selected",
                message=combined_message,
                history=history,
                forced_intent=profile.get("intent"),
                conversation_id=conversation_id,
                user_id=user_id,
                video_language=video_language,
            )

            return result

        # -------------------------------------------------------------
        # IMPORTANT CONTEXT CHECK
        #
        # If the previous turn established an emotion/problem and the
        # current message asks for a video/article/resource/exercise,
        # handle the request using the remembered context BEFORE running
        # emotion classification again.
        # -------------------------------------------------------------

        remembered_emotion = state.get("selected_emotion")
        remembered_profile = state.get("last_profile")

        if remembered_emotion:
            contextual_profile = build_problem_profile(
                message or "",
                emotion=remembered_emotion,
                confidence=None,
                history=history,
            )

            contextual_intent = contextual_profile.get("intent")

            if contextual_intent in {
                "video_request",
                "article_request",
                "resource_request",
                "exercise_request",
            }:
                return self._final_response(
                    remembered_emotion,
                    model_confidence=None,
                    classification_method="user_selected",
                    message=message,
                    history=history,
                    forced_intent=contextual_intent,
                    context_profile=remembered_profile,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    video_language=video_language,
                )

        # -------------------------------------------------------------
        # Normal emotion classification.
        # -------------------------------------------------------------

        emotion, confidence, all_scores = _classifier.predict(message)
        emotion = emotion or "neutral"

        profile = build_problem_profile(
            message,
            emotion=emotion,
            confidence=confidence,
            history=history,
        )

        intent = profile["intent"]

        is_low_information = emotion == "confusion"

        follow_ups_remaining = (
            state.get("follow_up_count", 0)
            < config.MAX_FOLLOW_UP_QUESTIONS
        )

        # -------------------------------------------------------------
        # Sufficient confidence and enough information.
        # -------------------------------------------------------------

        if (
            confidence >= config.CONFIDENCE_THRESHOLD
            and not is_low_information
            and follow_ups_remaining
        ):
            return self._final_response(
                emotion,
                confidence,
                "model",
                all_scores=all_scores,
                message=message,
                history=history,
                forced_intent=intent,
                conversation_id=conversation_id,
                user_id=user_id,
                video_language=video_language,
            )

        # -------------------------------------------------------------
        # Maximum follow-ups reached.
        # -------------------------------------------------------------

        if (
            state.get("follow_up_count", 0)
            >= config.MAX_FOLLOW_UP_QUESTIONS
        ):
            return self._final_response(
                emotion,
                confidence,
                "model",
                all_scores=all_scores,
                message=message,
                history=history,
                forced_intent=intent,
                conversation_id=conversation_id,
                user_id=user_id,
                video_language=video_language,
            )

        # -------------------------------------------------------------
        # Ask the guided emotion question.
        # -------------------------------------------------------------

        new_state = dict(state)

        new_state["awaiting_guided_choice"] = True
        new_state["follow_up_count"] = (
            state.get("follow_up_count", 0) + 1
        )
        new_state["pending_intent"] = intent

        return {
            "type": "clarify",
            "reply": gq.GUIDED_PROMPT,
            "emotion": emotion,
            "model_confidence": confidence,
            "classification_method": "model",
            "resources": [],
            "guided_options": [
                option["label"]
                for option in gq.PRIMARY_OPTIONS
            ],
            "correctable": False,
            "problem_profile": profile,
            "state": new_state,
        }

    # -----------------------------------------------------------------
    # Emotion correction
    # -----------------------------------------------------------------

    def correct(
        self,
        predicted_emotion: str,
        corrected_emotion: str,
        message: str = "",
        history=None,
        conversation_id=None,
        user_id=None,
        video_language="en",
    ):
        """
        Rebuild the response using the user's corrected emotion.

        message/history are accepted so the original problem context can
        still be used when generating resources.
        """

        result = self._final_response(
            corrected_emotion,
            model_confidence=None,
            classification_method="user_selected",
            message=message,
            history=history,
            conversation_id=conversation_id,
            user_id=user_id,
            video_language=video_language,
        )

        result["reply"] = (
            f"{CORRECTION_ACKNOWLEDGEMENT} "
            f"{result['reply']}"
        )

        return result

    # -----------------------------------------------------------------
    # Final response + resource selection
    # -----------------------------------------------------------------

    def _final_response(
        self,
        emotion,
        model_confidence,
        classification_method,
        all_scores=None,
        message="",
        history=None,
        forced_intent=None,
        context_profile=None,
        conversation_id=None,
        user_id=None,
        video_language="en",
    ):
        profile = build_problem_profile(
            message or "",
            emotion=emotion,
            confidence=model_confidence,
            history=history,
            forced_intent=forced_intent,
        )

        # When this is a follow-up resource request, preserve the
        # previously established problem/context information.
        if context_profile:
            profile = self._merge_profiles(
                context_profile,
                profile,
            )

        intent = profile["intent"]

        resources = []

        wants_resource = intent in {
            "video_request",
            "article_request",
            "resource_request",
            "exercise_request",
        }

        # -------------------------------------------------------------
        # Resource recommendation
        # -------------------------------------------------------------

        if wants_resource:

            # ---------------------------------------------------------
            # Video request
            # ---------------------------------------------------------

            if intent == "video_request":

                previously_recommended = []

                if user_id is not None:
                    try:
                        previously_recommended = (
                            db.get_recommended_video_ids(user_id)
                        )
                    except Exception:
                        logger.exception(
                            "Could not retrieve video recommendation history "
                            "for user_id=%r",
                            user_id,
                        )

                resources = get_video_resources(
                    profile,
                    exclude_ids=previously_recommended,
                )

                # Save newly selected curated videos.
                if resources and user_id is not None:
                    for resource in resources:
                        video_id = resource.get("id")

                        if video_id is None:
                            continue

                        try:
                            db.save_video_recommendation(
                                user_id=user_id,
                                conversation_id=conversation_id,
                                video_id=str(video_id),
                            )
                        except Exception:
                            logger.exception(
                                "Could not save video recommendation "
                                "for user_id=%r, video_id=%r",
                                user_id,
                                video_id,
                            )

                # If no unused curated video exists, try the
                # personalized-video fallback.
                if not resources:
                    try:
                        from personalized_video.video_manager import (
                            create_or_reuse_video
                        )

                        generated = create_or_reuse_video(
                            profile,
                            conversation_id=conversation_id,
                            language=video_language,
                        )

                        if generated:
                            resources = [generated]

                    except Exception:
                        logger.exception(
                            "Personalized video generation failed."
                        )
                        resources = []

            # ---------------------------------------------------------
            # Article request
            # ---------------------------------------------------------

            elif intent == "article_request":
                resources = get_resources(emotion)

            # ---------------------------------------------------------
            # Exercise request
            # ---------------------------------------------------------

            elif intent == "exercise_request":
                resources = [
                    resource
                    for resource in get_resources(emotion)
                    if resource.get("resource_type") == "exercise"
                ]

            # ---------------------------------------------------------
            # General resource request
            # ---------------------------------------------------------

            else:
                previously_recommended = []

                if user_id is not None:
                    try:
                        previously_recommended = (
                            db.get_recommended_video_ids(user_id)
                        )
                    except Exception:
                        logger.exception(
                            "Could not retrieve video recommendation history "
                            "for user_id=%r",
                            user_id,
                        )

                resources = (
                    get_resources(emotion)
                    + get_video_resources(
                        profile,
                        exclude_ids=previously_recommended,
                    )
                )

        # -------------------------------------------------------------
        # Base supportive response
        # -------------------------------------------------------------

        reply = SUPPORTIVE_TEMPLATES.get(
            emotion,
            SUPPORTIVE_TEMPLATES["neutral"],
        )

        if intent == "video_request" and not resources:
            reply += (
                " I couldn't prepare a matching video right now, "
                "but we can keep talking about what you're dealing with."
            )

        # -------------------------------------------------------------
        # IMPORTANT:
        # Preserve emotion + profile for the next user turn.
        # -------------------------------------------------------------

        return {
            "type": "response",
            "reply": reply,
            "emotion": emotion,
            "model_confidence": model_confidence,
            "classification_method": classification_method,
            "all_scores": all_scores,
            "resources": resources,
            "problem_profile": profile,
            "guided_options": None,
            "correctable": classification_method == "model",
            "state": self._state_after_response(
                emotion,
                profile,
            ),
        }


dialogue_manager = DialogueManager()
