"""
db.py

CONCEPT (Part 36 - Application Architecture):
------------------------------------------------
All SQL lives here, and nowhere else. routes/*.py call these functions;
they never build SQL strings themselves. This does two things:

1. Keeps responsibilities separated (routes handle HTTP, db.py handles
   persistence) per Part 36's recommended layering.
2. Makes SQL injection protection auditable in one file: every query below
   uses parameterized placeholders (%s), never Python string formatting
   or f-strings to build a query (Part 26).

ERROR HANDLING (Part 38): every public function here can raise
mysql.connector.Error. Callers (routes) are responsible for catching it
and returning a friendly message - this module does not swallow errors
silently, because the caller needs to know a write failed.
"""

import logging
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import config

logger = logging.getLogger("mh_chatbot.db")


def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        port=config.DB_PORT,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


# ---------------------------------------------------------------------
# Users (Parts 16, 23)
# ---------------------------------------------------------------------
def create_user(username: str, password: str):
    """Returns the new user_id. Raises mysql.connector.IntegrityError if
    the username is already taken (caught by the route)."""
    password_hash = generate_password_hash(password)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def verify_login(username: str, password: str):
    """Returns the user dict (without password_hash) on success, else None.
    Never logs the password itself (Part 29)."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return None


    return {"user_id": user["id"], "username": user["username"]}

# ---------------------------------------------------------------------
# Conversations & messages (Part 22)
# ---------------------------------------------------------------------
def start_conversation(user_id: int) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO conversations (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def end_conversation(conversation_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE conversations SET ended_at = NOW() WHERE id = %s", (conversation_id,))
        conn.commit()
    finally:
        conn.close()


def save_message(conversation_id: int, sender: str, message_text: str) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (conversation_id, sender, message) VALUES (%s, %s, %s)",
            (conversation_id, sender, message_text),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Emotion analysis (Part 7 - FIX: classification_method distinction)
# ---------------------------------------------------------------------
def save_emotion_analysis(message_id: int, predicted_emotion: str, model_confidence, classification_method: str):
    """
    IMPORTANT (Part 7): model_confidence is a real probability ONLY when
    classification_method == 'model'. For 'user_selected' input it MUST be
    stored as NULL - a button click is not a model probability and must
    never be recorded as confidence = 1.0.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO emotion_analysis (message_id, predicted_emotion, model_confidence, classification_method) "
            "VALUES (%s, %s, %s, %s)",
            (message_id, predicted_emotion, model_confidence, classification_method),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------
# User feedback / correction (Part 16)
# ---------------------------------------------------------------------
def save_user_feedback(message_id: int, predicted_emotion: str, user_selected_emotion: str):
    """The user disagreed with (or confirmed) the bot's interpretation.
    Storing both values lets the model's real-world error rate be measured
    later without ever claiming the original prediction was correct."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_feedback (message_id, predicted_emotion, user_selected_emotion) "
            "VALUES (%s, %s, %s)",
            (message_id, predicted_emotion, user_selected_emotion),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# ---------------------------------------------------------------------
# Conversation context / generated video records
# ---------------------------------------------------------------------
def get_recent_messages(conversation_id: int, limit: int = 8):
    """Return recent conversation messages for contextual personalization."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sender, message, created_at FROM messages "
            "WHERE conversation_id = %s ORDER BY id DESC LIMIT %s",
            (conversation_id, int(limit)),
        )
        rows = cur.fetchall()
        return list(reversed(rows))
    finally:
        conn.close()


def save_generated_video(conversation_id: int, problem_signature: str,
                         script: str, video_path: str, status: str = "completed"):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO generated_videos "
            "(conversation_id, problem_signature, script, video_path, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (conversation_id, problem_signature, script, video_path, status),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def find_generated_video(conversation_id: int, problem_signature: str):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM generated_videos "
            "WHERE conversation_id = %s AND problem_signature = %s "
            "AND status = 'completed' ORDER BY id DESC LIMIT 1",
            (conversation_id, problem_signature),
        )
        return cur.fetchone()
    finally:
        conn.close()

# ---------------------------------------------------------------------
# Curated video recommendation history
# ---------------------------------------------------------------------

def get_recommended_video_ids(user_id: int):
    """
    Return the IDs of curated videos that have already been
    recommended to this user.

    These IDs are used by recommender.py to avoid repeatedly
    recommending the same curated video.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT video_id FROM video_recommendations "
            "WHERE user_id = %s",
            (user_id,),
        )

        rows = cur.fetchall()

        return [row[0] for row in rows]

    finally:
        conn.close()


def save_video_recommendation(
    user_id: int,
    conversation_id: int,
    video_id: str,
):
    """
    Record that a curated video was recommended to a user.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO video_recommendations "
            "(user_id, conversation_id, video_id) "
            "VALUES (%s, %s, %s)",
            (
                user_id,
                conversation_id,
                str(video_id),
            ),
        )

        conn.commit()

        return cur.lastrowid

    finally:
        conn.close()
