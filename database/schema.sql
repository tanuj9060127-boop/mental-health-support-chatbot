-- database/schema.sql
--
-- CHANGE LOG vs. the previous prototype schema:
--   - conversations: added ended_at (Part 22)
--   - emotion_analysis: renamed 'confidence' -> 'model_confidence' and added
--     'classification_method' (Part 7 fix: user-selected emotions must not
--     be stored as confidence = 1.0)
--   - NEW user_feedback table (Part 16 - user correction)
--   - resources: expanded to id/title/description/category/url/source/active
--     (Part 20/22), placeholder example.org rows removed entirely
--
-- PRIVACY NOTE (Part 30): only fields needed to run the adaptive
-- conversation and demonstrate the project are collected. No profile data,
-- no location, no device fingerprinting.

CREATE DATABASE IF NOT EXISTS mh_chatbot
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE mh_chatbot;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(40) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender ENUM('user', 'bot') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_messages_conversation_id_id (conversation_id, id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Part 7 fix: model_confidence is NULL whenever classification_method is
-- 'user_selected' - a guided-menu click is not a model probability.
CREATE TABLE IF NOT EXISTS emotion_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    predicted_emotion VARCHAR(40),
    model_confidence FLOAT NULL,
    classification_method ENUM('model', 'user_selected') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Part 16: lets a user correct the chatbot's interpretation. Both values
-- are kept so the model's real disagreement rate can be measured later -
-- this is NOT used to silently "fix" model_prediction after the fact.
CREATE TABLE IF NOT EXISTS user_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    predicted_emotion VARCHAR(40),
    user_selected_emotion VARCHAR(40),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Part 20/22: resources are primarily managed via resources/resources.json
-- (the app reads from there at runtime - see resources/recommender.py).
-- This table mirrors that file for reporting/admin queries; keep them in
-- sync manually, or extend recommender.py to read from this table instead
-- if you want a single source of truth.
CREATE TABLE IF NOT EXISTS resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(40) NOT NULL,
    url VARCHAR(500) NOT NULL,
    source VARCHAR(255),
    active BOOLEAN DEFAULT TRUE
);


-- Personalized video generation records. The chatbot stores only the
-- generated script/path and a compact problem signature needed to avoid
-- unnecessary regeneration within a conversation.
CREATE TABLE IF NOT EXISTS generated_videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    problem_signature VARCHAR(128) NOT NULL,
    script TEXT NOT NULL,
    video_path VARCHAR(500) NOT NULL,
    status ENUM('pending', 'generating', 'completed', 'failed') NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_generated_video_lookup (conversation_id, problem_signature)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Personalized curated-video recommendation history.
-- Stores which curated videos have already been recommended so the
-- recommender can avoid repeatedly showing the same video.
CREATE TABLE IF NOT EXISTS video_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    conversation_id INT NOT NULL,
    video_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE,

    INDEX idx_video_recommendation_user (
        user_id,
        video_id
    ),

    INDEX idx_video_recommendation_conversation (
        conversation_id,
        video_id
    )
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
