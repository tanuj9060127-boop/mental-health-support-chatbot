"""Registration, login and logout routes."""

import logging

from flask import Blueprint, redirect, render_template, request, session, url_for
import mysql.connector

import db
from validators import ValidationError, validate_password, validate_username

logger = logging.getLogger("mh_chatbot.auth")
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("index.html", mode="register")

    try:
        username = validate_username(request.form.get("username", ""))
        password = validate_password(request.form.get("password", ""))
    except ValidationError as exc:
        return render_template("index.html", mode="register", error=str(exc)), 400

    try:
        db.create_user(username, password)
    except mysql.connector.IntegrityError:
        return render_template("index.html", mode="register", error="Username already taken."), 409
    except mysql.connector.Error:
        logger.warning("Database error during registration.", exc_info=True)
        return render_template(
            "index.html",
            mode="register",
            error="We couldn't complete registration right now. Please try again shortly.",
        ), 503

    logger.info("A user account was registered.")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("index.html", mode="login")

    try:
        username = validate_username(request.form.get("username", ""))
        password = validate_password(request.form.get("password", ""))
    except ValidationError:
        # Use one message for malformed/unknown credentials to avoid exposing account details.
        return render_template("index.html", mode="login", error="Invalid username or password."), 401

    try:
        user = db.verify_login(username, password)
    except mysql.connector.Error:
        logger.warning("Database error during login.", exc_info=True)
        return render_template(
            "index.html",
            mode="login",
            error="We couldn't log you in right now. Please try again shortly.",
        ), 503

    if not user:
        logger.info("A login attempt was rejected.")
        return render_template("index.html", mode="login", error="Invalid username or password."), 401

    # Discard any pre-login state to avoid session fixation.
    session.clear()
    session.permanent = True
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    logger.info("A user signed in successfully.")
    return redirect(url_for("chat.chat_page"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    conversation_id = session.get("conversation_id")
    if conversation_id:
        try:
            db.end_conversation(conversation_id)
        except mysql.connector.Error:
            logger.warning("Could not mark the conversation as ended.", exc_info=True)
    session.clear()
    return redirect(url_for("auth.login"))
