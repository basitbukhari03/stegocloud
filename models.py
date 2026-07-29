"""
models.py - Database Models
StegoCloud: Steganography-Based Cloud Data Protection System

Tables:
    User       – registered accounts
    StegoFile  – uploaded steganographic images
    AuditLog   – security event log
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────────────────────
# User Model
# ─────────────────────────────────────────────────────────────────────────────
class User(db.Model, UserMixin):
    """Registered user account."""

    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(16),  default="user", nullable=False)   # 'admin' | 'user'
    mfa_secret    = db.Column(db.String(64),  nullable=True)
    mfa_enabled   = db.Column(db.Boolean,     default=False)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    is_active     = db.Column(db.Boolean,     default=True)

    # Brute-force tracking (not in UI, but used server-side)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until    = db.Column(db.DateTime, nullable=True)

    # Relationships
    files = db.relationship("StegoFile", backref="owner", lazy=True,
                            foreign_keys="StegoFile.owner_id")
    logs  = db.relationship("AuditLog",  backref="user",  lazy=True,
                            foreign_keys="AuditLog.user_id")

    def is_admin(self):
        return self.role == "admin"

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.username}>"


# ─────────────────────────────────────────────────────────────────────────────
# StegoFile Model
# ─────────────────────────────────────────────────────────────────────────────
class StegoFile(db.Model):
    """Record of a steganographic image stored in cloud_storage/."""

    __tablename__ = "stego_files"

    id                   = db.Column(db.Integer, primary_key=True)
    filename             = db.Column(db.String(256), nullable=False)          # stored filename
    original_image_name  = db.Column(db.String(256), nullable=False)          # user's original filename
    owner_id             = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_size            = db.Column(db.Integer, default=0)                   # bytes
    encryption_key_hint  = db.Column(db.String(32), nullable=True)            # first 3 chars + '***'
    upload_date          = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed        = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<StegoFile {self.filename}>"


# ─────────────────────────────────────────────────────────────────────────────
# AuditLog Model
# ─────────────────────────────────────────────────────────────────────────────
class AuditLog(db.Model):
    """Security event audit trail."""

    __tablename__ = "audit_logs"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username   = db.Column(db.String(64),  nullable=False, default="anonymous")
    action     = db.Column(db.String(32),  nullable=False)   # LOGIN|HIDE|EXTRACT|FAILED_LOGIN|LOGOUT
    details    = db.Column(db.String(512), nullable=True)
    ip_address = db.Column(db.String(45),  nullable=True)
    timestamp  = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.username}>"
