"""
steganography.py - LSB Steganography Module
StegoCloud: Steganography-Based Cloud Data Protection System

Implements Least Significant Bit (LSB) steganography using Pillow only.
Each character of the secret is encoded across the R, G, B channels of
sequential pixels by replacing their least significant bits.

Delimiter: the 16-bit sequence "1111111111111110" signals the end of data.
"""

from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

DELIMITER = "1111111111111110"   # 16 sentinel bits marking end-of-message


def _str_to_bits(text: str) -> str:
    """Convert a UTF-8 string to a flat binary string (8 bits per char)."""
    bits = []
    for char in text.encode("utf-8"):
        bits.append(format(char, "08b"))
    return "".join(bits)


def _bits_to_str(bits: str) -> str:
    """Convert a flat binary string back to a UTF-8 string (8 bits per char)."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if len(byte) < 8:
            break
        chars.append(chr(int(byte, 2)))
    return "".join(chars)


def _set_lsb(channel_value: int, bit: str) -> int:
    """Replace the least-significant bit of a single channel byte."""
    if bit == "1":
        return channel_value | 1     # force LSB to 1
    else:
        return channel_value & ~1    # force LSB to 0


# ─────────────────────────────────────────────────────────────────────────────
# Capacity
# ─────────────────────────────────────────────────────────────────────────────

def calculate_capacity(image_path: str) -> dict:
    """
    Calculate how many characters can be hidden inside the given image.

    Each pixel provides 3 bits (R, G, B LSB).
    We need 8 bits per encoded UTF-8 byte, plus 16 bits for the delimiter.

    Args:
        image_path: Absolute or relative path to the cover image.

    Returns:
        dict with 'bits', 'bytes', 'characters', 'pixels'.
    """
    img  = Image.open(image_path).convert("RGB")
    w, h = img.size
    total_pixels = w * h

    total_bits       = total_pixels * 3           # 3 channels × 1 LSB each
    usable_bits      = total_bits - len(DELIMITER) # reserve space for delimiter
    usable_bytes     = usable_bits // 8
    usable_chars     = usable_bytes                # 1 ASCII char = 1 byte; UTF-8 may vary

    return {
        "bits":       usable_bits,
        "bytes":      usable_bytes,
        "characters": usable_chars,
        "pixels":     total_pixels,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Hide
# ─────────────────────────────────────────────────────────────────────────────

def hide_data_in_image(image_path: str, secret_data: str, output_path: str) -> str:
    """
    Embed *secret_data* into the cover image using LSB steganography.

    Steps:
      1. Convert secret_data to binary bits.
      2. Append the 16-bit DELIMITER.
      3. Walk pixels; for each R/G/B channel replace LSB with one data bit.
      4. Save the modified image as PNG (lossless, preserves LSBs).

    Args:
        image_path:  Path to the cover (carrier) image.
        secret_data: Plaintext string to embed (should already be encrypted).
        output_path: Where to save the resulting stego image.

    Returns:
        output_path on success.

    Raises:
        ValueError: If the image is too small to hold the data.
        IOError:    If the image cannot be opened/saved.
    """
    img     = Image.open(image_path).convert("RGB")
    pixels  = list(img.getdata())
    width, height = img.size

    # Build the bit stream: data bits + delimiter
    binary_data = _str_to_bits(secret_data) + DELIMITER
    total_bits  = len(binary_data)

    # Capacity check: each pixel holds 3 bits
    max_bits = len(pixels) * 3
    if total_bits > max_bits:
        raise ValueError(
            f"Image too small! Need {total_bits} bits but image only holds "
            f"{max_bits} bits. Use a larger image or a shorter message."
        )

    new_pixels = []
    bit_index  = 0

    for pixel in pixels:
        r, g, b = pixel

        # Modify R channel
        if bit_index < total_bits:
            r = _set_lsb(r, binary_data[bit_index])
            bit_index += 1

        # Modify G channel
        if bit_index < total_bits:
            g = _set_lsb(g, binary_data[bit_index])
            bit_index += 1

        # Modify B channel
        if bit_index < total_bits:
            b = _set_lsb(b, binary_data[bit_index])
            bit_index += 1

        new_pixels.append((r, g, b))

        # Stop once all bits are embedded
        if bit_index >= total_bits:
            # Append remaining unchanged pixels
            new_pixels.extend(pixels[len(new_pixels):])
            break

    # Reconstruct the image
    stego_img = Image.new("RGB", (width, height))
    stego_img.putdata(new_pixels)
    stego_img.save(output_path, "PNG")

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Extract
# ─────────────────────────────────────────────────────────────────────────────

def extract_data_from_image(image_path: str) -> str:
    """
    Extract hidden data from a stego image by reading the LSB of each channel.

    Reads bits until the 16-bit DELIMITER is encountered, then converts the
    collected bit string back to the original UTF-8 string.

    Args:
        image_path: Path to the stego image.

    Returns:
        Recovered hidden string (still encrypted if it was encrypted before hiding).

    Raises:
        ValueError: If no hidden data or DELIMITER is found.
    """
    img    = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())

    bits = []

    for pixel in pixels:
        for channel in pixel:                       # R, G, B
            bits.append(str(channel & 1))           # read LSB

            # Check for trailing delimiter every 16 bits
            if len(bits) >= len(DELIMITER):
                tail = "".join(bits[-len(DELIMITER):])
                if tail == DELIMITER:
                    # Strip the delimiter and convert to string
                    data_bits = "".join(bits[:-len(DELIMITER)])
                    return _bits_to_str(data_bits)

    raise ValueError(
        "No hidden data found in this image. "
        "It may not be a StegoCloud image or may be corrupted."
    )
