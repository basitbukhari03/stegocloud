"""
demo_encryption.py - AES-256 Encryption Demo
StegoCloud: Steganography-Based Cloud Data Protection System

Demonstrates AES-256-CBC encrypt → decrypt roundtrip with multiple examples.

Usage:
    python demo_encryption.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encryption import encrypt_message, decrypt_message, get_key_hint


# ─────────────────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────────────────

def demo(label: str, message: str, password: str) -> bool:
    print(f"\n  {'─'*54}")
    print(f"  Case     : {label}")
    print(f"  Message  : {message[:60]}{'…' if len(message)>60 else ''}")
    print(f"  Password : {get_key_hint(password)} (hint)")

    encrypted = encrypt_message(message, password)
    print(f"  Encrypted: {encrypted[:60]}…")

    try:
        decrypted = decrypt_message(encrypted, password)
        match = decrypted == message
        print(f"  Decrypted: {decrypted[:60]}{'…' if len(decrypted)>60 else ''}")
        print(f"  Match?   : {'✅ YES' if match else '❌ NO'}")
        return match
    except ValueError as e:
        print(f"  Error    : {e}")
        return False


def demo_wrong_password(label: str, message: str, right_pw: str, wrong_pw: str):
    print(f"\n  {'─'*54}")
    print(f"  Case     : {label}")
    encrypted = encrypt_message(message, right_pw)
    try:
        decrypt_message(encrypted, wrong_pw)
        print(f"  ❌ Should have raised ValueError but didn't!")
    except ValueError:
        print(f"  ✅ Correctly rejected wrong password '{get_key_hint(wrong_pw)}'")


def main():
    print("=" * 60)
    print("  StegoCloud – AES-256 Encryption Demo")
    print("=" * 60)

    tests = [
        ("Simple string",    "Hello, World!",                    "MyPassword1!"),
        ("Long message",     "Secret data: " + "X" * 500,       "Str0ng#Pass"),
        ("Special chars",    "Héllo 🔐 你好 <>&\"'",             "p@$$w0rd!"),
        ("JSON content",     '{"key":"value","num":42}',         "Json@Key99"),
        ("Empty-ish",        " ",                                "MinP@ss1"),
        ("Numeric",          "1234567890" * 10,                  "Numer1c!"),
    ]

    passed = sum(1 for label, msg, pw in tests if demo(label, msg, pw))

    print(f"\n  {'─'*54}")
    print(f"  Wrong-password rejection tests:")
    demo_wrong_password("Wrong password",     "Secret!",  "CorrectP@ss1", "WrongPass1!")
    demo_wrong_password("Empty wrong password","Others",  "Right@123",    "")

    print(f"\n{'═'*60}")
    print(f"  Encrypt/decrypt: {passed}/{len(tests)} passed")
    if passed == len(tests):
        print("  ✅ ALL ENCRYPTION TESTS PASSED!")
    else:
        print("  ❌ SOME TESTS FAILED.")
    print("=" * 60)

    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
