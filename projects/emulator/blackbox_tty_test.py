#!/usr/bin/env python3
"""
Blackbox TTY test for squash game.

Spawns emulator_runner under a real PTY in --gui mode with squash.elf,
injects 'w' and 's' keypresses through the PTY master fd (like a real
keyboard), and captures ASCII screenshots from the terminal output.

Uses adaptive frame reading: after injecting a key, waits until the
paddle position actually changes before taking the screenshot.
"""

import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

EMULATOR_DIR = Path(__file__).resolve().parent
BUILD_DIR = EMULATOR_DIR / "build"
DEFAULT_RUNNER = BUILD_DIR / "emulator_runner"
ELF = BUILD_DIR / "squash.elf"

FRAME_W = 20
FRAME_H = 20
ESC = b"\x1b[2J\x1b[H"


class FrameReader:
    """Reads ANSI terminal frames from a PTY master fd."""

    def __init__(self, fd, frame_h):
        self.fd = fd
        self.frame_h = frame_h
        self.buffer = b""
        self.raw = b""

    def _read(self, timeout=0.1):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return b""
        try:
            data = os.read(self.fd, 65536)
            if data:
                self.raw += data
            return data
        except OSError:
            return b""

    def _extract_frame(self):
        idx = self.buffer.rfind(ESC)
        if idx == -1:
            self.buffer = self.buffer[-4096:]
            return None
        self.buffer = self.buffer[idx + len(ESC):]
        while self.buffer[:1] in (b"\r", b"\n"):
            self.buffer = self.buffer[1:]

        lines = []
        pos = 0
        for _ in range(self.frame_h):
            nl = self.buffer.find(b"\n", pos)
            if nl == -1:
                return None
            line = self.buffer[pos:nl]
            if line.endswith(b"\r"):
                line = line[:-1]
            lines.append(line.decode("ascii", errors="ignore"))
            pos = nl + 1
        self.buffer = self.buffer[pos:]
        return lines

    def read_frame(self, timeout=6.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.buffer += self._read(0.1)
            frame = self._extract_frame()
            if frame is not None:
                return frame
        raise AssertionError("Timed out waiting for GUI frame")


def normalize_frame(lines, w=FRAME_W):
    out = []
    for line in lines:
        if len(line) < w:
            line = line.ljust(w)
        out.append(line[:w])
    return out


def frame_text(lines):
    return "\n".join(normalize_frame(lines)) + "\n"


def find_paddle_top(lines, h=FRAME_H):
    """Find the top row of the paddle (4+ consecutive rows of #### at left edge)."""
    normed = normalize_frame(lines, FRAME_W)
    actual_h = min(h, len(normed))
    # The paddle is 4+ consecutive rows with '####' in columns 0-3
    consecutive = 0
    first_row = None
    for y in range(1, actual_h - 1):
        if normed[y][:4] == "####":
            if consecutive == 0:
                first_row = y
            consecutive += 1
            if consecutive >= 3:
                return first_row
        else:
            consecutive = 0
            first_row = None
    return None


def is_game_over(lines):
    """Check if the frame shows the X loss pattern instead of a game scene."""
    normed = normalize_frame(lines, FRAME_W)
    actual_h = min(FRAME_H, len(normed))
    # X pattern has # at diagonal positions across the frame
    x_count = 0
    for y in range(1, actual_h - 1):
        for x in range(1, FRAME_W - 1):
            d1 = x - y
            d2 = x - (actual_h - 2 - y)
            if (abs(d1) <= 1 or abs(d2) <= 1) and normed[y][x] == "#":
                x_count += 1
    # A real game scene has paddle (4+ rows of #### in cols 1-3) and walls
    # An X pattern has scattered # across diagonals
    paddle_rows = 0
    for y in range(1, actual_h - 1):
        if normed[y][:4] == "####":
            paddle_rows += 1
    # If very few paddle rows but lots of diagonal #, it's likely an X
    return paddle_rows < 3 and x_count > 30


def shutdown(proc, mfd):
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    finally:
        try:
            os.close(mfd)
        except OSError:
            pass


def spawn_gui(runner):
    mfd, sfd = pty.openpty()
    proc = subprocess.Popen(
        [str(runner), str(ELF), "--gui", "--gui-cycles", "50000"],
        stdin=sfd,
        stdout=sfd,
        stderr=sfd,
    )
    os.close(sfd)
    return proc, mfd


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Blackbox TTY test for squash game")
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER,
                        help="Path to emulator_runner or verilator_runner binary")
    args = parser.parse_args()

    runner = args.runner
    if not runner.exists():
        print(f"ERROR: runner not found at {runner}")
        sys.exit(1)
    if not ELF.exists():
        print(f"ERROR: squash.elf not found at {ELF}")
        sys.exit(1)

    print(f"Using runner: {runner}")
    proc, mfd = spawn_gui(runner)
    reader = FrameReader(mfd, FRAME_H)

    print("Waiting for emulator to initialize...")
    time.sleep(3)

    screenshots = {}

    # --- Initial frame (no key) ---
    print("Capturing initial frame (waiting for game to render)...")
    initial_paddle = None
    for _ in range(15):
        try:
            frame = reader.read_frame(timeout=6.0)
        except AssertionError:
            frame = None
        if frame and not is_game_over(frame):
            pt = find_paddle_top(frame)
            if pt is not None:
                screenshots["initial"] = frame
                initial_paddle = pt
                print(f"  OK - paddle at row {pt}")
                break
        time.sleep(0.3)
    else:
        print("  WARNING: game did not render in time")
        screenshots["initial"] = [" " * FRAME_W] * FRAME_H

    # --- Press 'w' and wait for paddle to move up ---
    print("Injecting 'w' key via PTY (waiting for paddle to move up)...")
    os.write(mfd, b"w")
    w_paddle = initial_paddle
    for _ in range(20):
        try:
            frame = reader.read_frame(timeout=6.0)
        except AssertionError:
            frame = None
        if frame and not is_game_over(frame):
            pt = find_paddle_top(frame)
            if pt is not None and initial_paddle is not None and pt < initial_paddle:
                screenshots["after_w"] = frame
                w_paddle = pt
                print(f"  OK - paddle moved from row {initial_paddle} to {pt}")
                break
        time.sleep(0.3)
    else:
        # Take whatever frame we have
        try:
            frame = reader.read_frame(timeout=3.0)
        except AssertionError:
            frame = None
        if frame:
            screenshots["after_w"] = frame
            w_paddle = find_paddle_top(frame)
        print(f"  WARNING: paddle may not have moved (current row: {w_paddle})")

    # --- Press 's' and wait for paddle to move down ---
    print("Injecting 's' key via PTY (waiting for paddle to move down)...")
    os.write(mfd, b"s")
    s_paddle = w_paddle
    for _ in range(20):
        try:
            frame = reader.read_frame(timeout=6.0)
        except AssertionError:
            frame = None
        if frame and not is_game_over(frame):
            pt = find_paddle_top(frame)
            if pt is not None and w_paddle is not None and pt > w_paddle:
                screenshots["after_s"] = frame
                s_paddle = pt
                print(f"  OK - paddle moved from row {w_paddle} to {pt}")
                break
        time.sleep(0.3)
    else:
        try:
            frame = reader.read_frame(timeout=3.0)
        except AssertionError:
            frame = None
        if frame:
            screenshots["after_s"] = frame
            s_paddle = find_paddle_top(frame)
        print(f"  WARNING: paddle may not have moved (current row: {s_paddle})")

    # Shutdown
    shutdown(proc, mfd)

    # --- Print ASCII screenshots ---
    print()
    print("=" * 60)
    print("BLACKBOX TTY SCREENSHOTS")
    print("=" * 60)

    for label, frame in screenshots.items():
        print(f"\n--- {label.upper()} ---")
        print(frame_text(frame))

    # --- Paddle analysis ---
    iy = find_paddle_top(screenshots.get("initial", []))
    wy = find_paddle_top(screenshots.get("after_w", []))
    sy = find_paddle_top(screenshots.get("after_s", []))

    print("--- PADDLE ANALYSIS ---")
    print(f"  Initial paddle top row: {iy}")
    print(f"  After 'w' paddle top row: {wy}")
    print(f"  After 's' paddle top row: {sy}")

    if iy is not None and wy is not None:
        dw = wy - iy
        direction = "up" if dw < 0 else "down" if dw > 0 else "no change"
        print(f"  'w' moved paddle from row {iy} to {wy} ({direction} by {abs(dw)} rows)")

    if wy is not None and sy is not None:
        ds = sy - wy
        direction = "up" if ds < 0 else "down" if ds > 0 else "no change"
        print(f"  's' moved paddle from row {wy} to {sy} ({direction} by {abs(ds)} rows)")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
