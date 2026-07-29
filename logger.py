"""
logger.py - Audit Logging Helper
StegoCloud: Steganography-Based Cloud Data Protection System

Writes security events both to the SQLite AuditLog table  
and to a rotating file log under logs/.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


# ─────────────────────────────────────────────────────────────────────────────
# File Logger Setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_file_logger(log_folder: str) -> logging.Logger:
    """
    Create and configure a rotating file logger for the application.

    Args:
        log_folder: Directory where log files are stored.

    Returns:
        Configured Logger instance.
    """
    os.makedirs(log_folder, exist_ok=True)

    logger = logging.getLogger("stegocloud")
    logger.setLevel(logging.INFO)

    # Rotate at 5 MB, keep 5 backup files
    handler = RotatingFileHandler(
        os.path.join(log_folder, "stegocloud.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Helper (writes to DB)
# ─────────────────────────────────────────────────────────────────────────────

def log_action(user_id, username: str, action: str, details: str, ip_address: str):
    """
    Record a security event in the SQLite AuditLog table.

    Import is deferred to avoid circular imports at module load time.

    Args:
        user_id:    Integer user PK (or None for anonymous).
        username:   Display name for the actor.
        action:     One of LOGIN | HIDE | EXTRACT | FAILED_LOGIN | LOGOUT | REGISTER | DELETE.
        details:    Free-text description of the event.
        ip_address: Originating IP of the request.
    """
    from models import db, AuditLog   # deferred to avoid circular import

    entry = AuditLog(
        user_id    = user_id,
        username   = username,
        action     = action,
        details    = details,
        ip_address = ip_address,
        timestamp  = datetime.utcnow(),
    )
    db.session.add(entry)
    db.session.commit()

    # Also write to the rotating file log
    file_logger = logging.getLogger("stegocloud")
    file_logger.info("[%s] %s – %s | IP: %s", action, username, details, ip_address)
