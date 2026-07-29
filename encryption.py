"""
encryption.py - AES-256-CBC Encryption / Decryption Module
StegoCloud: Steganography-Based Cloud Data Protection System

Uses PyCryptodome for AES-256 in CBC mode with PKCS7 padding.
The encryption key is derived from the user's password via SHA-256.
"""

import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


# ─────────────────────────────────────────────────────────────────────────────
# Key Derivation
# ─────────────────────────────────────────────────────────────────────────────

def _derive_key(password: str) -> bytes:
    """
    Derive a 32-byte AES key from a plaintext password using SHA-256.

    Args:
        password: User-supplied plaintext password string.

    Returns:
        32-byte key suitable for AES-256.
    """
    return hashlib.sha256(password.encode("utf-8")).digest()


# ─────────────────────────────────────────────────────────────────────────────
# Encryption
# ─────────────────────────────────────────────────────────────────────────────

def encrypt_message(message: str, password: str) -> str:
    """
    Encrypt a plaintext message with AES-256-CBC.

    The format of the returned string is:
        base64(iv) + ":" + base64(ciphertext)

    Args:
        message:  Plaintext string to encrypt.
        password: Password from which the key is derived.

    Returns:
        Encrypted string in "iv_b64:ct_b64" format.
    """
    key = _derive_key(password)

    # Random 16-byte Initialisation Vector (makes each encryption unique)
    iv = get_random_bytes(16)

    # Encrypt with PKCS7 padding so the message length is a multiple of 16
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(message.encode("utf-8"), AES.block_size))

    # Encode both IV and ciphertext to base64 for safe string transport
    iv_b64 = base64.b64encode(iv).decode("utf-8")
    ct_b64 = base64.b64encode(ciphertext).decode("utf-8")

    return f"{iv_b64}:{ct_b64}"


# ─────────────────────────────────────────────────────────────────────────────
# Decryption
# ─────────────────────────────────────────────────────────────────────────────

def decrypt_message(encrypted_str: str, password: str) -> str:
    """
    Decrypt an AES-256-CBC encrypted string.

    Args:
        encrypted_str: String in "iv_b64:ct_b64" format (produced by encrypt_message).
        password:      The same password used during encryption.

    Returns:
        Original plaintext string.

    Raises:
        ValueError: If the password is wrong or the data is corrupted.
    """
    try:
        parts = encrypted_str.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid encrypted format – expected 'iv:ciphertext'.")

        iv         = base64.b64decode(parts[0])
        ciphertext = base64.b64decode(parts[1])

        key = _derive_key(password)

        # Decrypt and remove PKCS7 padding
        cipher    = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)

        return plaintext.decode("utf-8")

    except (ValueError, KeyError, Exception) as exc:
        raise ValueError(f"Decryption failed – wrong password or corrupted data. ({exc})")


# ─────────────────────────────────────────────────────────────────────────────
# Key Hint Helper
# ─────────────────────────────────────────────────────────────────────────────

def get_key_hint(password: str) -> str:
    """
    Return a safe hint string showing only the first 3 characters of the password,
    followed by asterisks.  Never store the full password.

    Args:
        password: User-supplied plaintext password.

    Returns:
        Hint string, e.g.  "Sec***" for "SecretKey".
    """
    if len(password) <= 3:
        return password[:1] + "***"
    return password[:3] + "***"
