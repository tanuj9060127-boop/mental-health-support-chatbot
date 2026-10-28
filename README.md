# Mental Health Support Chatbot

A student project that combines a rule-based dialogue flow, a small text emotion classifier, curated wellbeing resources, and locally rendered personalized educational videos. Generated videos can include spoken narration in **English or Hindi**.

> **Scope and safety:** This is a prototype for educational use. It is not a diagnostic system, a crisis service, or a substitute for professional care. The emotion model and keyword-based safety check are not clinically validated.

## Features

- Registration and login with hashed passwords.
- Flask + MySQL persistence for users, conversations, messages, emotion analyses, user corrections, and generated-video metadata.
- TF-IDF + logistic-regression classification across seven language-emotion labels: anger, confusion, fear, joy, neutral, sadness, and stress.
- Guided emotion selection when the classifier is uncertain, plus user correction.
- Context-aware curated article/video recommendations. Previously shown curated videos are excluded from later recommendations for that user.
- Personalized educational slideshow videos with embedded narration in English or Hindi. The narration is generated from controlled, generic text based on broad problem/context tags; the user's raw chat message is not read aloud.
- CSRF protection for form and API POST requests, input validation, safe text rendering in the browser, and safer session-cookie defaults.

## Requirements

- Python 3.11 or newer (the bundled model was re-trained with scikit-learn 1.8.0).
- MySQL Server 8.x or a compatible MySQL release.
- An internet connection when generating spoken narration through gTTS.
- A Devanagari-capable font for Hindi captions. Windows systems commonly have Nirmala UI; Linux servers may need Noto Sans Devanagari. Set `HINDI_FONT_PATH` if automatic font discovery cannot find one.

## Setup on Windows / VS Code

Open PowerShell in the project directory (`mh_chatbot`) and run:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in VS Code and set a local database username/password. Do not put real secrets into `.env.example`, source files, screenshots, or Git commits. Generate a secret key with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy that value into `SECRET_KEY` in `.env`. For local development the app creates a random temporary key if `SECRET_KEY` is blank, but the session will be invalidated whenever the app restarts. A fixed `SECRET_KEY` is required for stable sessions, and production mode refuses to start without one.

### Database setup

Run `database/schema.sql` in MySQL Workbench, or execute it from a terminal with the MySQL command-line client. It creates the `mh_chatbot` database and required tables, using `utf8mb4` so Hindi scripts can be stored correctly.

A dedicated database account is preferable to using `root`. After creating the database and tables, an administrator can create a restricted local account with permissions appropriate for this app, for example:

```sql
CREATE USER 'mh_chatbot_app'@'localhost' IDENTIFIED BY 'choose-a-strong-local-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON mh_chatbot.* TO 'mh_chatbot_app'@'localhost';
```

Put that account's details in `.env` (`DB_USER`, `DB_PASSWORD`, and `DB_NAME`). Do not commit the actual `.env` file. If you have an older database created with a different character set, run `database/migrate_utf8mb4.sql` against that database to convert existing tables to `utf8mb4`.

### Run the app

Make sure your virtual environment is active, then run:

```powershell
python app.py
```

Open <http://127.0.0.1:5000> in the same computer. Use the app's **Generated video narration** selector to choose English or Hindi before asking for a video. The selected language applies to newly generated videos; curated third-party videos keep their original language.

The Flask development server is for local development only. Do not expose it directly to the public internet. A real deployment needs a production WSGI server, HTTPS, deployment-specific secret management, monitoring, data-retention rules, and privacy/legal review.

## How generated videos work

1. The dialogue manager builds a structured problem profile from the conversation.
2. The video recommender first looks for an unused, relevant curated video in `resources/videos.json`.
3. If a video is explicitly requested and no unused curated video matches, the generator creates a controlled English or Hindi script.
4. The script passes through a phrase-based safety check.
5. Pillow and imageio render the caption slides. gTTS generates spoken narration, and FFmpeg muxes the audio into the final MP4.
6. The generated file is stored under `static/generated_videos/` and served by Flask at a `/static/...` URL.

Voice generation requires a working internet connection. If narration cannot be generated or audio/video validation fails, the app does **not** silently return a silent MP4. Hindi captions require a font with Devanagari glyphs. To keep the user's exact message private, the narration uses controlled labels such as “academic pressure” or “family expectations,” rather than reading the raw message aloud.

**Third-party processing note:** gTTS uses an online speech service. Only the generic narration text generated by this project is submitted to that service, not the raw chat message, but the service is still an external dependency. For sensitive production use, replace `personalized_video/tts.py` with a privacy-reviewed local TTS engine or an explicitly consented provider.

## Model evaluation and limitations

The included dataset has 284 hand-written examples across seven emotion labels. The current fixed-seed evaluation reported:

- Validation accuracy: **0.628**
- Held-out test accuracy: **0.558** on 43 examples

These results describe only this small dataset and split; they are not a claim of real-world accuracy. The model has known weaknesses with negation, sarcasm, mixed emotions, and phrasing unlike the training examples. A high model score is not a clinical confidence measure. The model classifies wording; it does not identify a medical condition.

The crisis check is a simple English keyword list. It can miss indirect, multilingual, or otherwise unrecognized language and cannot assess risk. If a message indicates a possible crisis, the application points users toward emergency support and external crisis directories, but this logic must never be treated as a reliable crisis detector.

## Tests

Run the test suite from the project root:

```powershell
pytest -q
```

The tests cover the classifier, dialogue flow, validation, safety logic, recommendation filtering, script language selection, and MP4 audio muxing. The audio-mux test uses a locally generated test tone rather than contacting the online speech service. Database integration tests are skipped unless the configured MySQL database is reachable; run them against a **disposable test database**, not real user data.

To retrain and re-evaluate the model after changing `emotion/dataset.csv`:

```powershell
python evaluate_model.py
```

This command overwrites `emotion/model.joblib` and `emotion/evaluation_report.txt`. The checked-in model should be loaded with the pinned scikit-learn version in `requirements.txt` to avoid pickle-version warnings.

## Data and GitHub hygiene

- `.env`, virtual environments, Python caches, logs, database exports, audio temporary files, and generated MP4 files are excluded by `.gitignore`.
- Keep real user conversations and MySQL dumps out of the repository. The application stores conversation text in the configured MySQL database; this prototype does not currently provide user-facing data export/deletion controls.
- If a credential was ever committed, rotate it and clean the repository history before publishing. Deleting a secret in a later commit does not remove it from earlier Git history.
- Make the repository private while auditing. Publish it only after the code, documentation, tests, and data handling have been reviewed.

## Project structure

```text
mh_chatbot/
├── app.py
├── config.py
├── db.py
├── validators.py
├── database/
│   ├── schema.sql
│   └── migrate_utf8mb4.sql
├── dialogue/
│   ├── manager.py
│   ├── problem_analyzer.py
│   ├── safety.py
│   └── guided_questions.py
├── emotion/
│   ├── classifier.py
│   ├── dataset.csv
│   ├── evaluation_report.txt
│   └── model.joblib
├── personalized_video/
│   ├── script_generator.py
│   ├── safety_checker.py
│   ├── tts.py
│   ├── video_generator.py
│   └── video_manager.py
├── resources/
│   ├── resources.json
│   ├── videos.json
│   └── recommender.py
├── routes/
├── static/
├── templates/
└── tests/
```
