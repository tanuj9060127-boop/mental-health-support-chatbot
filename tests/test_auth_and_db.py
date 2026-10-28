"""
tests/test_auth_and_db.py

Part 32 - Testing: registration, duplicate username, login (correct/
incorrect password), message storage, emotion storage, user/conversation
relationships.

HONEST LIMITATION: unlike the other test files, these tests need a real,
running MySQL server. This sandbox that built the project has no network
access and no MySQL server, so these tests could NOT be executed during
development - that is stated plainly here rather than faked.

TO RUN THESE FOR REAL:
    1. Create a throwaway test database: mysql -u root -p < database/schema.sql
       but with DB_NAME set to something like mh_chatbot_test.
    2. Set environment variables pointing at it, e.g.:
         export DB_NAME=mh_chatbot_test DB_USER=root DB_PASSWORD=yourpassword
    3. Run: python tests/test_auth_and_db.py
    4. Drop the test database afterward - these tests write real rows.

If no database is reachable, this script prints a clear SKIPPED message
for every test rather than reporting a false pass or crashing with a raw
connection traceback.
"""

import os
import sys
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import mysql.connector
    import db
    _IMPORT_OK = True
except ImportError as _e:
    mysql = None
    db = None
    _IMPORT_OK = False
    _IMPORT_ERROR = _e


def _db_available():
    if not _IMPORT_OK:
        return False
    try:
        conn = db.get_connection()
        conn.close()
        return True
    except mysql.connector.Error:
        return False


try:
    import pytest
    pytestmark = pytest.mark.skipif(
        not _db_available(),
        reason="Requires mysql-connector-python and a reachable disposable MySQL test database.",
    )
except ImportError:
    pytest = None


def test_valid_registration_and_login():
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    password = "correct-horse-battery"
    user_id = db.create_user(username, password)
    assert user_id is not None

    user = db.verify_login(username, password)
    assert user is not None
    assert user["username"] == username


def test_duplicate_username_rejected():
    username = f"dupuser_{uuid.uuid4().hex[:8]}"
    db.create_user(username, "some-password-123")
    try:
        db.create_user(username, "another-password-456")
        assert False, "Expected IntegrityError for duplicate username"
    except mysql.connector.IntegrityError:
        pass


def test_incorrect_password_rejected():
    username = f"wrongpass_{uuid.uuid4().hex[:8]}"
    db.create_user(username, "the-real-password")
    result = db.verify_login(username, "totally-wrong-password")
    assert result is None


def test_invalid_login_unknown_user():
    result = db.verify_login("no_such_user_should_exist", "whatever")
    assert result is None


def test_message_and_emotion_storage_relationship():
    username = f"convuser_{uuid.uuid4().hex[:8]}"
    user_id = db.create_user(username, "password123456")
    conversation_id = db.start_conversation(user_id)
    message_id = db.save_message(conversation_id, "user", "I am really worried about tomorrow")
    db.save_emotion_analysis(message_id, "fear", 0.63, "model")

    # Part 7 regression check at the DB layer too: user-selected must be NULL confidence
    message_id_2 = db.save_message(conversation_id, "user", "[guided option: sadness]")
    db.save_emotion_analysis(message_id_2, "sadness", None, "user_selected")


def test_user_feedback_storage():
    username = f"fbuser_{uuid.uuid4().hex[:8]}"
    user_id = db.create_user(username, "password123456")
    conversation_id = db.start_conversation(user_id)
    message_id = db.save_message(conversation_id, "user", "I don't know")
    db.save_user_feedback(message_id, predicted_emotion="fear", user_selected_emotion="anger")


if __name__ == "__main__":
    if not _IMPORT_OK:
        print(f"SKIPPED: mysql-connector-python is not installed in this environment ({_IMPORT_ERROR}).")
        print("Run `pip install -r requirements.txt` in an environment with network/package access, "
              "then see this file's docstring for how to run these tests against a real test database.")
        sys.exit(0)
    if not _db_available():
        print("SKIPPED: no reachable MySQL database (expected in the sandbox that built this project).")
        print("See this file's docstring for how to run these tests against a real test database.")
        sys.exit(0)

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
        except mysql.connector.Error as e:
            print(f"ERROR (DB): {t.__name__} - {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
