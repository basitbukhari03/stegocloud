"""
app.py - Main Application Entry Point
StegoCloud: Steganography-Based Cloud Data Protection System

Registers blueprints (auth_bp, main_bp, admin_bp), initialises extensions,
creates the database on first run, and seeds demo data.

Run with:
    python app.py
"""

import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_from_directory, jsonify,
    abort, session,
)
from flask_login import (
    LoginManager, login_required, current_user,
)
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

from config   import Config
from models   import db, User, StegoFile, AuditLog
from logger   import setup_file_logger, log_action
from auth     import auth_bp, admin_required


# ─────────────────────────────────────────────────────────────────────────────
# Application Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    bcrypt      = Bcrypt(app)
    csrf        = CSRFProtect(app)
    login_mgr   = LoginManager(app)

    login_mgr.login_view       = "auth.login"
    login_mgr.login_message    = "Please log in to access this page."
    login_mgr.login_message_category = "warning"

    @login_mgr.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── File logger ───────────────────────────────────────────────────────────
    setup_file_logger(app.config["LOG_FOLDER"])

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"]        = "SAMEORIGIN"
        response.headers["X-XSS-Protection"]       = "1; mode=block"
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        return response

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)

    # Register main and admin blueprints defined below inside factory scope
    _register_main_routes(app, bcrypt)
    _register_admin_routes(app)

    # ── DB init & seed ────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        seed_db(bcrypt)

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Main Blueprint Routes
# ─────────────────────────────────────────────────────────────────────────────

def _register_main_routes(app: Flask, bcrypt: Bcrypt):
    from flask import Blueprint
    from encryption   import encrypt_message, decrypt_message, get_key_hint
    from steganography import hide_data_in_image, extract_data_from_image, calculate_capacity

    main_bp = Blueprint("main", __name__)

    # ── Landing page ──────────────────────────────────────────────────────────
    @main_bp.route("/")
    def index():
        return render_template("index.html")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    @main_bp.route("/dashboard")
    @login_required
    def dashboard():
        from sqlalchemy import func
        uid = current_user.id

        total_files    = StegoFile.query.filter_by(owner_id=uid).count()
        total_hides    = AuditLog.query.filter_by(user_id=uid, action="HIDE").count()
        total_extracts = AuditLog.query.filter_by(user_id=uid, action="EXTRACT").count()
        recent_logs    = (AuditLog.query
                          .filter_by(user_id=uid)
                          .order_by(AuditLog.timestamp.desc())
                          .limit(10).all())

        # Activity data for last 7 days (Chart.js)
        from datetime import timedelta
        labels, hides_data, extracts_data = [], [], []
        today = datetime.utcnow().date()
        for i in range(6, -1, -1):
            day   = today - timedelta(days=i)
            start = datetime.combine(day, datetime.min.time())
            end   = datetime.combine(day, datetime.max.time())
            labels.append(day.strftime("%d %b"))
            hides_data.append(
                AuditLog.query.filter(
                    AuditLog.user_id == uid,
                    AuditLog.action  == "HIDE",
                    AuditLog.timestamp.between(start, end)
                ).count()
            )
            extracts_data.append(
                AuditLog.query.filter(
                    AuditLog.user_id == uid,
                    AuditLog.action  == "EXTRACT",
                    AuditLog.timestamp.between(start, end)
                ).count()
            )

        # File-size distribution for pie chart
        files = StegoFile.query.filter_by(owner_id=uid).all()
        size_labels, size_data = [], []
        for f in files:
            size_labels.append(f.filename[:20])
            size_data.append(f.file_size)

        return render_template(
            "dashboard.html",
            total_files    = total_files,
            total_hides    = total_hides,
            total_extracts = total_extracts,
            recent_logs    = recent_logs,
            chart_labels      = labels,
            chart_hides       = hides_data,
            chart_extracts    = extracts_data,
            pie_labels        = size_labels,
            pie_data          = size_data,
        )

    # ── Hide Data ─────────────────────────────────────────────────────────────
    @main_bp.route("/hide", methods=["GET", "POST"])
    @login_required
    def hide():
        if request.method == "POST":
            cover_image  = request.files.get("cover_image")
            secret_msg   = request.form.get("secret_message", "").strip()
            enc_password = request.form.get("enc_password", "")
            conf_password= request.form.get("conf_password", "")

            # ── Validation ───────────────────────────────────────────────────
            errors = []
            if not cover_image or cover_image.filename == "":
                errors.append("Please upload a cover image.")
            if not secret_msg:
                errors.append("Secret message cannot be empty.")
            if not enc_password:
                errors.append("Encryption password is required.")
            if enc_password != conf_password:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("hide_data.html")

            # ── File type validation (magic bytes) ───────────────────────────
            filename_lower = cover_image.filename.lower()
            if not filename_lower.endswith((".png", ".jpg", ".jpeg")):
                flash("Only PNG and JPG images are allowed.", "danger")
                return render_template("hide_data.html")

            # ── Save uploaded cover image temporarily ─────────────────────────
            tmp_name = f"tmp_{uuid.uuid4().hex}_{cover_image.filename}"
            tmp_path = os.path.join(app.config["UPLOAD_FOLDER"], tmp_name)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            cover_image.save(tmp_path)

            try:
                # ── Capacity check ───────────────────────────────────────────
                cap = calculate_capacity(tmp_path)
                encrypted_msg = encrypt_message(secret_msg, enc_password)
                if len(encrypted_msg) + 16 > cap["characters"]:
                    os.remove(tmp_path)
                    flash(
                        f"Image too small! Capacity: {cap['characters']} chars, "
                        f"your encrypted message: {len(encrypted_msg)} chars. "
                        "Use a larger image.", "danger"
                    )
                    return render_template("hide_data.html")

                # ── Embed ────────────────────────────────────────────────────
                out_name = f"stego_{uuid.uuid4().hex}.png"
                out_path = os.path.join(app.config["UPLOAD_FOLDER"], out_name)
                hide_data_in_image(tmp_path, encrypted_msg, out_path)

                # ── Save record ──────────────────────────────────────────────
                file_size = os.path.getsize(out_path)
                record = StegoFile(
                    filename            = out_name,
                    original_image_name = cover_image.filename,
                    owner_id            = current_user.id,
                    file_size           = file_size,
                    encryption_key_hint = get_key_hint(enc_password),
                    upload_date         = datetime.utcnow(),
                )
                db.session.add(record)
                db.session.commit()

                log_action(current_user.id, current_user.username, "HIDE",
                           f"Hidden data in '{out_name}' (size={file_size}B).",
                           request.remote_addr)

                flash("Data hidden successfully! Download your stego image below.", "success")
                return render_template(
                    "hide_data.html",
                    success       = True,
                    stego_filename= out_name,
                    original_name = cover_image.filename,
                    capacity      = cap,
                    msg_length    = len(secret_msg),
                )
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return render_template("hide_data.html")
            finally:
                # Clean up temp file (keep stego output)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        return render_template("hide_data.html")

    # ── Extract Data ──────────────────────────────────────────────────────────
    @main_bp.route("/extract", methods=["GET", "POST"])
    @login_required
    def extract():
        if request.method == "POST":
            stego_image  = request.files.get("stego_image")
            dec_password = request.form.get("dec_password", "")

            if not stego_image or stego_image.filename == "":
                flash("Please upload a stego image.", "danger")
                return render_template("extract_data.html")
            if not dec_password:
                flash("Decryption password is required.", "danger")
                return render_template("extract_data.html")

            # ── Save image temporarily ────────────────────────────────────────
            tmp_name = f"extr_{uuid.uuid4().hex}_{stego_image.filename}"
            tmp_path = os.path.join(app.config["UPLOAD_FOLDER"], tmp_name)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            stego_image.save(tmp_path)

            try:
                hidden_str    = extract_data_from_image(tmp_path)
                plaintext     = decrypt_message(hidden_str, dec_password)
                log_action(current_user.id, current_user.username, "EXTRACT",
                           f"Successful extraction from '{stego_image.filename}'.",
                           request.remote_addr)
                return render_template(
                    "extract_data.html",
                    success   = True,
                    plaintext = plaintext,
                )
            except ValueError as ve:
                msg = str(ve)
                if "Decryption failed" in msg or "padding" in msg.lower() or "MAC" in msg:
                    # Wrong password — AES decryption failed
                    log_action(current_user.id, current_user.username, "EXTRACT",
                               f"Failed extraction – wrong password for '{stego_image.filename}'.",
                               request.remote_addr)
                    return render_template("extract_data.html",
                                           success=False,
                                           error_type="wrong_password",
                                           filename=stego_image.filename)
                else:
                    # No hidden data found in image
                    return render_template("extract_data.html",
                                           success=False,
                                           error_type="no_data",
                                           filename=stego_image.filename)
            except Exception as exc:
                return render_template("extract_data.html",
                                       success=False,
                                       error_type="generic",
                                       error_msg=str(exc))
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        return render_template("extract_data.html")

    # ── My Files ──────────────────────────────────────────────────────────────
    @main_bp.route("/my-files")
    @login_required
    def my_files():
        files = (StegoFile.query
                 .filter_by(owner_id=current_user.id)
                 .order_by(StegoFile.upload_date.desc())
                 .all())
        return render_template("my_files.html", files=files)

    @main_bp.route("/delete-file/<int:file_id>", methods=["POST"])
    @login_required
    def delete_file(file_id):
        record = StegoFile.query.get_or_404(file_id)
        if record.owner_id != current_user.id and not current_user.is_admin():
            abort(403)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], record.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(record)
        db.session.commit()
        log_action(current_user.id, current_user.username, "DELETE",
                   f"Deleted file '{record.filename}'.", request.remote_addr)
        flash("File deleted successfully.", "success")
        return redirect(url_for("main.my_files"))

    # ── Download stego image ──────────────────────────────────────────────────
    @main_bp.route("/download/<filename>")
    @login_required
    def download_file(filename):
        record = StegoFile.query.filter_by(filename=filename).first_or_404()
        if record.owner_id != current_user.id and not current_user.is_admin():
            abort(403)
        record.last_accessed = datetime.utcnow()
        db.session.commit()
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename,
                                   as_attachment=True)

    # ── Audit logs — ADMIN ONLY ───────────────────────────────────────────────
    # Regular users cannot access audit logs (login times, IPs, actions).
    # Only admins can view logs via /admin/logs or /logs.
    @main_bp.route("/logs")
    @login_required
    def logs():
        # Block non-admin users from viewing any audit logs
        if not current_user.is_admin():
            flash("⛔ Access Denied – Audit logs are restricted to administrators only.", "danger")
            return redirect(url_for("main.dashboard"))

        # Admin: show all system logs
        all_logs = (AuditLog.query
                    .order_by(AuditLog.timestamp.desc())
                    .limit(500).all())
        return render_template("logs.html", logs=all_logs, admin_view=True)

    app.register_blueprint(main_bp)


# ─────────────────────────────────────────────────────────────────────────────
# Admin Blueprint Routes
# ─────────────────────────────────────────────────────────────────────────────

def _register_admin_routes(app: Flask):
    from flask import Blueprint
    admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

    @admin_bp.route("/")
    @login_required
    @admin_required
    def admin_panel():
        total_users   = User.query.count()
        active_users  = User.query.filter_by(is_active=True).count()
        total_files   = StegoFile.query.count()
        today_start   = datetime.utcnow().replace(hour=0, minute=0, second=0)
        ops_today     = AuditLog.query.filter(AuditLog.timestamp >= today_start).count()
        users         = User.query.order_by(User.created_at.desc()).all()
        recent_logs   = (AuditLog.query
                         .order_by(AuditLog.timestamp.desc())
                         .limit(50).all())
        return render_template(
            "admin.html",
            total_users  = total_users,
            active_users = active_users,
            total_files  = total_files,
            ops_today    = ops_today,
            users        = users,
            recent_logs  = recent_logs,
        )

    @admin_bp.route("/toggle-user", methods=["POST"])
    @login_required
    @admin_required
    def toggle_user():
        user_id = request.form.get("user_id", type=int)
        user    = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash("You cannot deactivate your own account.", "warning")
        else:
            user.is_active = not user.is_active
            db.session.commit()
            status = "activated" if user.is_active else "deactivated"
            flash(f"User '{user.username}' has been {status}.", "success")
            log_action(current_user.id, current_user.username, "ADMIN",
                       f"{status.title()} user '{user.username}'.",
                       request.remote_addr)
        return redirect(url_for("admin.admin_panel"))

    @admin_bp.route("/change-role", methods=["POST"])
    @login_required
    @admin_required
    def change_role():
        """Promote a user to admin OR demote an admin to user."""
        user_id  = request.form.get("user_id", type=int)
        new_role = request.form.get("new_role", "").strip()
        user     = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash("You cannot change your own role.", "warning")
            return redirect(url_for("admin.admin_panel"))

        if new_role not in ("admin", "user"):
            flash("Invalid role specified.", "danger")
            return redirect(url_for("admin.admin_panel"))

        # Safety: do not demote the last admin
        if new_role == "user" and user.role == "admin":
            admin_count = User.query.filter_by(role="admin").count()
            if admin_count <= 1:
                flash("Cannot demote the last administrator. Promote another user first.", "danger")
                return redirect(url_for("admin.admin_panel"))

        old_role     = user.role
        user.role    = new_role
        db.session.commit()

        action_desc = f"Promoted" if new_role == "admin" else "Demoted"
        flash(f"{action_desc} '{user.username}' from {old_role.upper()} to {new_role.upper()}.", "success")
        log_action(current_user.id, current_user.username, "ADMIN",
                   f"{action_desc} '{user.username}': {old_role} → {new_role}.",
                   request.remote_addr)
        return redirect(url_for("admin.admin_panel"))

    @admin_bp.route("/logs")
    @login_required
    @admin_required
    def admin_logs():
        all_logs = (AuditLog.query
                    .order_by(AuditLog.timestamp.desc())
                    .limit(500).all())
        return render_template("logs.html", logs=all_logs, admin_view=True)

    app.register_blueprint(admin_bp)


# ─────────────────────────────────────────────────────────────────────────────
# Database Seeder
# ─────────────────────────────────────────────────────────────────────────────

def seed_db(bcrypt: Bcrypt):
    """
    No demo accounts are seeded.
    The FIRST person to register at /register automatically becomes admin.
    All subsequent registrations create regular user accounts.
    """
    pass  # Fresh start — admin registers themselves on first run


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
