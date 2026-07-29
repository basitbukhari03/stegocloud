"""
test_steganography.py - Steganography Unit Tests
StegoCloud: Steganography-Based Cloud Data Protection System

Demonstrates that hide → extract recovers the EXACT original message.

Usage:
    python test_steganography.py
"""

import os
import sys
import tempfile
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from steganography import hide_data_in_image, extract_data_from_image, calculate_capacity


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_test_image(width: int = 800, height: int = 600, path: str = None) -> str:
    """Create a simple gradient PNG test image and save it."""
    if path is None:
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

    img = Image.new("RGB", (width, height))
    pixels = []
    for y in range(height):
        for x in range(width):
            r = (x * 255) // width
            g = (y * 255) // height
            b = 128
            pixels.append((r, g, b))
    img.putdata(pixels)
    img.save(path, "PNG")
    return path


def run_test(name: str, cover_path: str, message: str) -> bool:
    """Run a single hide/extract test. Returns True on pass."""
    print(f"\n{'─'*60}")
    print(f"  TEST: {name}")
    print(f"  Message length : {len(message)} chars")

    # ── Capacity check ────────────────────────────────────────────────────────
    cap = calculate_capacity(cover_path)
    print(f"  Image capacity : {cap['characters']} chars  ({cap['pixels']} pixels)")

    if len(message) > cap["characters"]:
        print(f"  ⚠  SKIP – message too long for this image ({len(message)} > {cap['characters']})")
        return True   # not a failure, just a skip

    # ── Hide ──────────────────────────────────────────────────────────────────
    fd, out_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        hide_data_in_image(cover_path, message, out_path)
        print(f"  ✔  Hidden successfully → {os.path.basename(out_path)}")
    except Exception as e:
        print(f"  ✗  HIDE FAILED: {e}")
        return False

    # ── Extract ───────────────────────────────────────────────────────────────
    try:
        recovered = extract_data_from_image(out_path)
    except Exception as e:
        print(f"  ✗  EXTRACT FAILED: {e}")
        os.remove(out_path)
        return False

    # ── Verify ────────────────────────────────────────────────────────────────
    if recovered == message:
        print(f"  ✔  EXTRACT MATCH – message recovered exactly!")
        result = True
    else:
        print(f"  ✗  MISMATCH!")
        print(f"     Expected : {message[:80]}")
        print(f"     Got      : {recovered[:80]}")
        result = False

    os.remove(out_path)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  StegoCloud – Steganography Test Suite")
    print("=" * 60)

    # Create a 800×600 test image
    cover = create_test_image(800, 600)
    print(f"\n  Cover image: {cover} (800×600 PNG)")

    tests = [
        ("Short message",        "Hello, StegoCloud!"),
        ("Medium message",       "This is a medium-length secret message for testing. " * 5),
        ("1000-character message","A" * 1000),
        ("Special characters",   "Héllo! 你好 مرحبا 🔐 <>&\"' \n\t special chars test."),
        ("JSON-like content",    '{"user":"alice","token":"abc123","data":[1,2,3]}'),
        ("Numeric string",       "1234567890" * 50),
    ]

    passed = 0
    failed = 0
    for name, msg in tests:
        ok = run_test(name, cover, msg)
        if ok:
            passed += 1
        else:
            failed += 1

    # Clean up
    os.remove(cover)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("  ✅ ALL TESTS PASSED – Steganography module is working correctly!")
    else:
        print("  ❌ SOME TESTS FAILED – Check the output above.")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
