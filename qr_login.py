#!/usr/bin/env python3
"""
Run openclaw WhatsApp login, capture QR codes, and save as a PNG image.

Usage:
    python3 /workspace/openclaw-whatsapp/qr_login.py

The QR code image is saved to /workspace/openclaw-whatsapp/qr_code.png
Each new QR code overwrites the previous one, so the file always contains
the latest scannable QR code.
The script exits after a successful link or when the login command ends.
"""
import subprocess
import os
import sys

QR_IMAGE_PATH = "/workspace/openclaw-whatsapp/qr_code.png"


def unicode_qr_to_image(qr_text, filename):
    """Convert a Unicode block QR code to a PNG image."""
    from PIL import Image

    lines = qr_text.strip().split("\n")
    # Each Unicode block char represents 2 vertical modules (top/bottom halves)
    # ▄ = bottom filled, ▀ = top filled, █ = both filled, ' ' = neither

    width = max(len(line) for line in lines)
    height = len(lines) * 2  # Each line encodes 2 rows

    scale = 8
    img = Image.new("RGB", (width * scale, height * scale), "white")
    pixels = img.load()

    for row_idx, line in enumerate(lines):
        for col_idx, char in enumerate(line):
            top_black = False
            bot_black = False
            if char == '\u2588':  # █ full block
                top_black = True
                bot_black = True
            elif char == '\u2580':  # ▀ upper half
                top_black = True
            elif char == '\u2584':  # ▄ lower half
                bot_black = True
            elif char == ' ':
                pass
            else:
                # Treat unknown chars as black (part of QR)
                top_black = True
                bot_black = True

            for dy in range(scale):
                for dx in range(scale):
                    if top_black:
                        pixels[col_idx * scale + dx, row_idx * 2 * scale + dy] = (0, 0, 0)
                    if bot_black:
                        pixels[col_idx * scale + dx, (row_idx * 2 + 1) * scale + dy] = (0, 0, 0)

    img.save(filename)
    print(f"Saved QR code image: {filename}", flush=True)


def main():
    proc = subprocess.Popen(
        ["openclaw", "channels", "login", "--channel", "whatsapp"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    qr_count = 0
    collecting_qr = False
    qr_lines = []

    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

        stripped = line.rstrip("\n")

        if "Scan this QR" in stripped:
            collecting_qr = True
            qr_lines = []
            continue

        if collecting_qr:
            if stripped.strip() == "":
                if qr_lines:
                    qr_count += 1
                    qr_text = "\n".join(qr_lines)
                    try:
                        unicode_qr_to_image(qr_text, QR_IMAGE_PATH)
                    except Exception as e:
                        print(f"Error saving QR image: {e}", flush=True)
                    collecting_qr = False
                    qr_lines = []
            else:
                qr_lines.append(stripped)

        if "Linked" in stripped or "ready" in stripped:
            break

    proc.wait()
    print(f"\nDone. Generated {qr_count} QR code(s). Latest image: {QR_IMAGE_PATH}", flush=True)


if __name__ == "__main__":
    main()
