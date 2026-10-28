"""Flask application factory and shared error handling."""

import logging
from datetime import timedelta

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

import config


def configure_logging():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger("mysql.connector").setLevel(logging.WARNING)


def create_app():
    configure_logging()
    logger = logging.getLogger("mh_chatbot.startup")

    # Fail at startup with a clear message rather than during a user's first chat.
    try:
        from emotion.classifier import EmotionClassifier
        EmotionClassifier()
    except Exception as exc:
        raise RuntimeError(
            f"Could not load the emotion model: {exc}. Check emotion/model.joblib and run `python evaluate_model.py` if needed."
        ) from exc

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        DEBUG=config.DEBUG,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=config.IS_PRODUCTION,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
        WTF_CSRF_TIME_LIMIT=3600,
    )
    CSRFProtect(app)

    from routes.auth_routes import auth_bp
    from routes.chat_routes import chat_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("chat.chat_page"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        logger.info("Rejected a request with an invalid or expired CSRF token.")
        message = "Your session token expired. Refresh the page and try again."
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), 400
        return render_template("error.html", message=message), 400

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("error.html", message="That page doesn't exist."), 404

    @app.errorhandler(500)
    def server_error(error):
        logger.error("Unhandled server error.", exc_info=True)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong on our end. Please try again."}), 500
        return render_template(
            "error.html",
            message="Something went wrong on our end. Please try again.",
        ), 500

    logger.info("Application started.")
    return app


app = create_app()


if __name__ == "__main__":
    # This is for local development only. Use a production WSGI server for deployment.
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
