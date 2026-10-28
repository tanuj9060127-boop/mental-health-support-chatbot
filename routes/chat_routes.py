"""
routes/chat_routes.py

CONCEPT (Part 36): chat-related HTTP handling only. All classification,
adaptive-questioning, and safety logic lives in dialogue/manager.py;
all SQL lives in db.py.

This file's job is:
    1. Validate HTTP input.
    2. Load conversation context.
    3. Call DialogueManager.
    4. Persist the turn.
    5. Return JSON.

Recommendation history:
    The logged-in user_id is passed to DialogueManager so personalized
    video recommendations can exclude videos already recommended to
    that user.
"""

import logging

from flask import (
    Blueprint,
    request,
    session,
    jsonify,
    render_template,
    redirect,
    url_for,
)

import mysql.connector

import config
import db
from dialogue.manager import DialogueManager
from validators import (
    validate_chat_message,
    validate_guided_emotion,
    validate_video_language,
    ValidationError,
)


logger = logging.getLogger("mh_chatbot.chat")

chat_bp = Blueprint("chat", __name__)

dialogue_manager = DialogueManager()


# ---------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------

def _login_required():
    return "user_id" in session


def _ensure_conversation():
    """Ensure the authenticated session has a database conversation."""
    conversation_id = session.get("conversation_id")
    if conversation_id:
        return conversation_id
    try:
        conversation_id = db.start_conversation(session["user_id"])
    except mysql.connector.Error:
        logger.warning("Could not start a conversation for the signed-in user.", exc_info=True)
        return None
    session["conversation_id"] = conversation_id
    session.setdefault("dialogue_state", dialogue_manager.new_state())
    return conversation_id


# ---------------------------------------------------------------------
# Chat page
# ---------------------------------------------------------------------

@chat_bp.route("/chat")
def chat_page():
    if not _login_required():
        return redirect(url_for("auth.login"))

    if _ensure_conversation() is None:
        return render_template(
            "error.html",
            message=(
                "We couldn't start a chat session right now. "
                "Please try again shortly."
            ),
        ), 503

    if "dialogue_state" not in session:
        session["dialogue_state"] = dialogue_manager.new_state()

    return render_template(
        "chat.html",
        username=session.get("username"),
    )


# ---------------------------------------------------------------------
# Main chat API
# ---------------------------------------------------------------------

@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():

    if not _login_required():
        return jsonify({
            "error": "not authenticated"
        }), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    conversation_id = _ensure_conversation()
    if conversation_id is None:
        return jsonify({"error": "Chat is temporarily unavailable. Please try again shortly."}), 503

    # -------------------------------------------------------------
    # Validate incoming message
    # -------------------------------------------------------------

    try:
        user_text = validate_chat_message(
            data.get("message")
        )

        guided_choice_made = (
            "guided_emotion" in data
        )

        guided_value = (
            validate_guided_emotion(data.get("guided_emotion"))
            if guided_choice_made
            else None
        )
        video_language = validate_video_language(data.get("video_language"))

    except ValidationError as e:
        return jsonify({
            "error": str(e)
        }), 400

    # -------------------------------------------------------------
    # Conversation state
    # -------------------------------------------------------------

    state = session.get(
        "dialogue_state",
        dialogue_manager.new_state(),
    )

    # -------------------------------------------------------------
    # Load recent conversation context
    # -------------------------------------------------------------

    try:
        history = db.get_recent_messages(
            conversation_id,
            limit=8,
        )

    except mysql.connector.Error as e:
        logger.warning(
            "Could not load recent conversation context: %s",
            e,
        )
        history = []

    # -------------------------------------------------------------
    # Call dialogue manager
    #
    # IMPORTANT:
    # user_id is passed so the video recommender can retrieve
    # previously recommended videos for this specific user.
    # -------------------------------------------------------------

    try:

        result = dialogue_manager.handle_message(
            user_text,
            state,
            guided_emotion=(
                guided_value
                if guided_choice_made
                else None
            ),
            history=history,
            conversation_id=conversation_id,
            user_id=session["user_id"],
            video_language=video_language,
        )

    except Exception as e:

        logger.exception(
            "Dialogue manager failure: %s",
            e,
        )

        result = {
            "type": "response",
            "reply": (
                "Thanks for sharing that. I'm having a little trouble "
                "processing things right now, but I'm still here - "
                "would you like to tell me more?"
            ),
            "emotion": None,
            "model_confidence": None,
            "classification_method": None,
            "resources": [],
            "guided_options": None,
            "correctable": False,
            "problem_profile": None,
            "state": dialogue_manager.new_state(),
        }

    # -------------------------------------------------------------
    # Persist the turn
    # -------------------------------------------------------------

    display_text = (
        user_text
        or f"[guided option: {data.get('guided_emotion')}]"
    )

    last_message_id = _persist_turn(
        conversation_id,
        display_text,
        result,
    )

    # -------------------------------------------------------------
    # Save updated dialogue state
    # -------------------------------------------------------------

    dialogue_state = result.get(
        "state",
        dialogue_manager.new_state(),
    )

    dialogue_state["last_message_id"] = last_message_id

    session["dialogue_state"] = dialogue_state

    # -------------------------------------------------------------
    # Return response
    # -------------------------------------------------------------

    return jsonify({
        "type": result.get("type"),
        "reply": result.get("reply"),
        "emotion": result.get("emotion"),
        "resources": result.get("resources", []),
        "guided_options": result.get("guided_options"),
        "correctable": result.get(
            "correctable",
            False,
        ),
    })


# ---------------------------------------------------------------------
# Emotion correction API
# ---------------------------------------------------------------------

@chat_bp.route("/api/correct", methods=["POST"])
def api_correct():
    """
    Part 16 - User Correction.

    The frontend calls this when the user says the bot's emotion
    prediction was incorrect.

    The original conversation context is loaded again so that correcting
    the emotion does not discard the user's actual problem.
    """

    if not _login_required():
        return jsonify({
            "error": "not authenticated"
        }), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    conversation_id = _ensure_conversation()
    if conversation_id is None:
        return jsonify({"error": "Chat is temporarily unavailable. Please try again shortly."}), 503

    try:
        video_language = validate_video_language(data.get("video_language"))
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    predicted_emotion = data.get("predicted_emotion")
    if not isinstance(predicted_emotion, str) or predicted_emotion not in config.KNOWN_EMOTIONS:
        return jsonify({"error": "Invalid predicted emotion."}), 400

    # Preserve the original user-message ID before the manager returns a
    # freshly reset dialogue state (which has last_message_id=None).
    message_id_to_correct = session.get("dialogue_state", {}).get("last_message_id")

    # -------------------------------------------------------------
    # Validate corrected emotion
    # -------------------------------------------------------------

    try:
        corrected_emotion = validate_guided_emotion(
            data.get("corrected_emotion")
        )

    except ValidationError as e:
        return jsonify({
            "error": str(e)
        }), 400

    if not corrected_emotion:
        return jsonify({
            "error": "A corrected emotion is required."
        }), 400

    # -------------------------------------------------------------
    # Load recent history for context.
    # -------------------------------------------------------------

    try:
        history = db.get_recent_messages(
            conversation_id,
            limit=8,
        )

    except mysql.connector.Error as e:
        logger.warning(
            "Could not load conversation history during correction: %s",
            e,
        )
        history = []

    # -------------------------------------------------------------
    # Find the most recent user message.
    #
    # This allows the corrected response to continue using the actual
    # problem instead of rebuilding a profile from an empty string.
    # -------------------------------------------------------------

    original_message = ""

    for item in reversed(history):
        if (
            isinstance(item, dict)
            and item.get("sender") == "user"
        ):
            original_message = (
                item.get("message") or ""
            )
            break

    # -------------------------------------------------------------
    # Re-run response generation using corrected emotion.
    # -------------------------------------------------------------

    try:

        result = dialogue_manager.correct(
            predicted_emotion,
            corrected_emotion,
            message=original_message,
            history=history,
            conversation_id=conversation_id,
            user_id=session["user_id"],
            video_language=video_language,
        )

    except Exception as e:

        logger.exception(
            "Emotion correction failure: %s",
            e,
        )

        return jsonify({
            "error": (
                "We couldn't apply the correction right now. "
                "Please try again."
            )
        }), 500

    # -------------------------------------------------------------
    # Preserve the existing state.
    # -------------------------------------------------------------

    session["dialogue_state"] = result.get(
        "state",
        dialogue_manager.new_state(),
    )
    session["dialogue_state"]["last_message_id"] = message_id_to_correct

    # -------------------------------------------------------------
    # Save feedback against the original user message.
    # -------------------------------------------------------------

    if message_id_to_correct:

        try:
            db.save_user_feedback(
                message_id_to_correct,
                predicted_emotion,
                corrected_emotion,
            )

        except mysql.connector.Error as e:
            logger.warning(
                "Could not persist user feedback: %s",
                e,
            )

    # -------------------------------------------------------------
    # Return corrected response.
    # -------------------------------------------------------------

    return jsonify({
        "type": result.get("type"),
        "reply": result.get("reply"),
        "emotion": result.get("emotion"),
        "resources": result.get("resources", []),
        "guided_options": None,
        "correctable": False,
    })


# ---------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------

def _persist_turn(
    conversation_id,
    user_text,
    result,
):
    """
    Save the user's message, emotion analysis, and bot reply.

    Returns:
        user_message_id on success.
        None if database persistence fails.

    A database failure does not block the chat response.
    """

    try:

        # ---------------------------------------------------------
        # Save user message
        # ---------------------------------------------------------

        user_message_id = db.save_message(
            conversation_id,
            "user",
            user_text,
        )

        # ---------------------------------------------------------
        # Save emotion analysis when available
        # ---------------------------------------------------------

        if (
            result.get("emotion") is not None
            and result.get("classification_method") is not None
        ):

            db.save_emotion_analysis(
                user_message_id,
                result.get("emotion"),
                result.get("model_confidence"),
                result.get("classification_method"),
            )

        # ---------------------------------------------------------
        # Save bot response
        # ---------------------------------------------------------

        db.save_message(
            conversation_id,
            "bot",
            result.get("reply", ""),
        )

        return user_message_id

    except mysql.connector.Error as e:

        logger.warning(
            "Could not persist chat turn: %s",
            e,
        )

        return None