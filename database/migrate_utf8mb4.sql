-- Run this only if mh_chatbot already exists with a non-utf8mb4 character set.
-- Back up the database first, especially if it contains real user data.
ALTER DATABASE mh_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mh_chatbot;
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE conversations CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE messages CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE emotion_analysis CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE user_feedback CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE resources CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE generated_videos CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE video_recommendations CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
