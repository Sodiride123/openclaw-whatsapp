#!/usr/bin/env python3
"""
Run openclaw WhatsApp login, capture the FIRST QR code, save it as a PNG
image, and exit immediately. The login process continues running in the
background so the QR code remains valid for scanning.

Usage:
    python3 /workspace/openclaw-whatsapp/qr_login.py

The QR code image is saved to /workspace/openclaw-whatsapp/qr_code.png
The script exits as soon as the first QR code image is saved.
The background login process (PID printed on exit) keeps running and will
complete once the user scans the code or it times out.
"""
import subprocess
import os
import sys
import signal

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
    print(f"QR code image saved: {filename}", flush=True)


def main():
    # Detach the child process from this script's process group so it
    # keeps running after we exit.
    proc = subprocess.Popen(
        ["openclaw", "channels", "login", "--channel", "whatsapp"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setpgrp,
    )

    collecting_qr = False
    qr_lines = []

    for line in proc.stdout:
        # Still print output so logs are visible if needed
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
                    qr_text = "\n".join(qr_lines)
                    try:
                        unicode_qr_to_image(qr_text, QR_IMAGE_PATH)
                    except Exception as e:
                        print(f"Error saving QR image: {e}", flush=True)
                        proc.terminate()
                        sys.exit(1)

                    # First QR code captured — exit immediately.
                    # The login process keeps running in the background.
                    print(f"Login process running in background (PID {proc.pid}).", flush=True)
                    print(f"It will complete automatically once the QR code is scanned.", flush=True)
                    sys.exit(0)
            else:
                qr_lines.append(stripped)

        # If login succeeded before we even got a QR (e.g. already linked)
        if "Linked" in stripped or "ready" in stripped:
            print("WhatsApp already linked — no QR code needed.", flush=True)
            sys.exit(0)

    # If we get here, the process ended without producing a QR code
    proc.wait()
    print("Login process ended without producing a QR code.", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
