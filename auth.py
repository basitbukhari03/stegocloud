"""
auth.py - Authentication Blueprint
StegoCloud: Steganography-Based Cloud Data Protection System

Routes:
    GET/POST /register        – new-account registration
    GET      /setup-mfa       – show QR code for Google Authenticator
    POST     /verify-mfa-setup – confirm the first OTP to activate MFA
    GET/POST /login           – step 1: username + password
    GET/POST /verify-mfa      – step 2: 6-digit TOTP
    GET      /logout          – destroy session
"""

import io
import re
import base64
from datetime import datetime, timedelta
from functools import wraps

import pyotp
import qrcode
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app, make_response,
)
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User
from logger import log_action

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_ip() -> str:
    """Return the real client IP, honouring X-Forwarded-For if present."""
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"


def _validate_password(password: str) -> list[str]:
    """
    Check password complexity rules.
    Returns a list of error messages.  Empty list means password is valid.
    """
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-\[\]\\\/\+\=\`\~\;\'\&]", password):
        errors.append("Password must contain at least one special character.")
    return errors


def admin_required(f):
    """Decorator: restrict route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Administrator access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return decorated


def _generate_qr_b64(totp_uri: str) -> str:
    """Generate a base64-encoded PNG QR code image from a TOTP provisioning URI."""
    qr     = qrcode.QRCode(version=1, box_size=6, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username         = request.form.get("username", "").strip()
        email            = request.form.get("email", "").strip().lower()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ── Basic field validation ──────────────────────────────────────────
        if not all([username, email, password, confirm_password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        pw_errors = _validate_password(password)
        if pw_errors:
            for err in pw_errors:
                flash(err, "danger")
            return render_template("register.html")

        # ── Uniqueness check ───────────────────────────────────────────────
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html")

        # ── Create user ────────────────────────────────────────────────────
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt(current_app)
        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        # ── Role assignment: first ever user becomes admin, rest are users ──
        # This ensures only ONE admin can exist (the system owner who registers first).
        admin_exists = User.query.filter_by(role="admin").first()
        assigned_role = "user" if admin_exists else "admin"

        user = User(
            username      = username,
            email         = email,
            password_hash = pw_hash,
            role          = assigned_role,
            is_active     = True,
        )
        db.session.add(user)
        db.session.commit()

        if assigned_role == "admin":
            flash("✅ Admin account created! You are the system administrator. Now set up 2FA.", "success")
        else:
            flash("Account created! Now set up 2-Factor Authentication.", "success")

        # Store user ID in session so setup_mfa can associate the secret
        session["mfa_setup_user_id"] = user.id
        return redirect(url_for("auth.setup_mfa"))

    return render_template("register.html")


# ─────────────────────────────────────────────────────────────────────────────
# MFA Setup
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/setup-mfa", methods=["GET"])
def setup_mfa():
    user_id = session.get("mfa_setup_user_id")
    if not user_id:
        flash("Please register first.", "warning")
        return redirect(url_for("auth.register"))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.register"))

    # Generate (or reuse) TOTP secret
    if not user.mfa_secret:
        user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    totp    = pyotp.TOTP(user.mfa_secret)
    uri     = totp.provisioning_uri(name=user.email, issuer_name="StegoCloud")
    qr_b64  = _generate_qr_b64(uri)

    return render_template(
        "setup_mfa.html",
        user     = user,
        qr_b64   = qr_b64,
        secret   = user.mfa_secret,
    )


@auth_bp.route("/verify-mfa-setup", methods=["POST"])
def verify_mfa_setup():
    user_id = session.get("mfa_setup_user_id")
    otp     = request.form.get("otp", "").strip()

    if not user_id:
        return redirect(url_for("auth.register"))

    user = User.query.get(user_id)
    if not user or not user.mfa_secret:
        flash("MFA setup error. Please register again.", "danger")
        return redirect(url_for("auth.register"))

    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(otp, valid_window=1):
        user.mfa_enabled = True
        db.session.commit()
        session.pop("mfa_setup_user_id", None)
        flash("MFA enabled successfully! Please log in.", "success")
        log_action(user.id, user.username, "REGISTER",
                   "Account registered and MFA activated.", _get_ip())
        return redirect(url_for("auth.login"))
    else:
        flash("Invalid OTP code. Please try again.", "danger")
        return redirect(url_for("auth.setup_mfa"))


# ─────────────────────────────────────────────────────────────────────────────
# Login – Step 1 (password)
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ip       = _get_ip()

        user = User.query.filter_by(username=username).first()

        # ── Account lock check ─────────────────────────────────────────────
        if user and user.locked_until and datetime.utcnow() < user.locked_until:
            remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            flash(f"Account locked. Try again in {remaining} minute(s).", "danger")
            log_action(user.id, username, "FAILED_LOGIN",
                       f"Login attempt on locked account.", ip)
            return render_template("login.html")

        # ── Password verification ──────────────────────────────────────────
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt(current_app)

        if user and user.is_active and bcrypt.check_password_hash(user.password_hash, password):
            # Reset failed-attempt counter on success
            user.failed_attempts = 0
            user.locked_until    = None
            db.session.commit()

            # Store partial auth in session; full login happens after TOTP
            session["pre_auth_user_id"] = user.id
            return redirect(url_for("auth.verify_mfa"))
        else:
            # Failed login
            if user:
                user.failed_attempts = (user.failed_attempts or 0) + 1
                if user.failed_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                    user.locked_until    = datetime.utcnow() + timedelta(
                        minutes=current_app.config["LOCKOUT_MINUTES"])
                    user.failed_attempts = 0
                    flash(f"Too many failed attempts. Account locked for "
                          f"{current_app.config['LOCKOUT_MINUTES']} minutes.", "danger")
                else:
                    remaining = current_app.config["MAX_LOGIN_ATTEMPTS"] - user.failed_attempts
                    flash(f"Invalid credentials. {remaining} attempt(s) remaining.", "danger")
                db.session.commit()
                log_action(user.id, username, "FAILED_LOGIN",
                           f"Failed password attempt #{user.failed_attempts}.", ip)
            else:
                flash("Invalid credentials.", "danger")
                log_action(None, username, "FAILED_LOGIN",
                           "Username not found.", ip)

    return render_template("login.html")


# ─────────────────────────────────────────────────────────────────────────────
# Login – Step 2 (TOTP)
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/verify-mfa", methods=["GET", "POST"])
def verify_mfa():
    user_id = session.get("pre_auth_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.login"))

    # ── If MFA not yet activated, send user to setup first ────────────────
    if not user.mfa_enabled:
        session["mfa_setup_user_id"] = user.id
        flash("Please complete 2FA setup before logging in.", "warning")
        return redirect(url_for("auth.setup_mfa"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        ip  = _get_ip()

        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(otp, valid_window=1):
            session.pop("pre_auth_user_id", None)
            login_user(user, remember=False)
            session.permanent = True
            log_action(user.id, user.username, "LOGIN",
                       "Successful login (password + TOTP).", ip)
            flash(f"Welcome back, {user.username}! 🔐", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid OTP code. Please try again.", "danger")
            log_action(user.id, user.username, "FAILED_LOGIN",
                       "Failed TOTP verification.", ip)

    return render_template("verify_mfa.html", username=user.username)


# ─────────────────────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user.id, current_user.username, "LOGOUT",
               "User logged out.", _get_ip())
    logout_user()
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))
