#!/usr/bin/env python3
"""
GUI smoke test for squash game: captures framebuffer at various cycle counts,
renders PPM images, and prints debug state.

Usage:
    pytest blackbox_tests/test_squash_gui.py -v              # run tests
    python3 blackbox_tests/test_squash_gui.py                # render PPMs manually
"""

from __future__ import annotations

import re
import struct
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
RUNNER = BUILD_DIR / "emulator_runner"
SQUASH_ELF = BUILD_DIR / "squash.elf"

FB_W = 20
FB_H = 15
FB_ADDR = "0x20000"
# Game writes fb[_y * 320 + _x]; each row is 320 bytes. We need 15 rows.
FB_STRIDE = 320
FB_BYTES = FB_STRIDE * FB_H  # 4800

DEBUG_WORD_ADDR = "0x153fe0"

debug_word_re = re.compile(r'0x00153fe0:\s+0x([0-9a-f]+)\s+\(')


def decode_debug_word(val: int) -> dict:
    ball_vy = val & 1
    ball_vx = (val >> 1) & 1
    rest = val - (ball_vx * 2 + ball_vy)
    rest //= 10
    game_state = rest % 10
    rest //= 10
    for bx in range(20):
        r2 = rest - bx * 100
        if r2 < 0:
            break
        by = r2 // 10
        py = r2 % 10
        if by < 15 and py < 11:
            return {"ball_x": bx, "ball_y": by, "paddle_y": py,
                    "game_state": game_state, "ball_vx": ball_vx, "ball_vy": ball_vy}
    return {"ball_x": -1, "ball_y": -1, "paddle_y": -1,
            "game_state": -1, "ball_vx": -1, "ball_vy": -1}


def run_squash(cycles: int, key: int = 0) -> tuple[bytes, int]:
    """Run emulator, return (framebuffer_bytes, debug_word)."""
    r = subprocess.run(
        [str(RUNNER), str(SQUASH_ELF),
         "--char-code", str(key),
         "--cycles", str(cycles),
         "--dump-memory", FB_ADDR, str(FB_BYTES),
         "--dump-memory", DEBUG_WORD_ADDR, "1"],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, f"emulator failed: {r.stderr}"

    # Parse full memory dump to extract framebuffer pixels
    fb = bytearray(FB_W * FB_H)
    row_vals = {}
    for line in r.stdout.split("\n"):
        # Format: "0x00020000: 0xXXXXXXXX (data)"
        if line.startswith("0x0002") and len(line) > 20:
            parts = line.split()
            if len(parts) >= 2:
                # Each line dumps multiple words; first word starts at 0x20000
                addr_str = parts[0].rstrip(':')
                base_addr = int(addr_str, 16)
                for p in parts[1:]:
                    if p.startswith("0x") and len(p) == 10:
                        word_val = int(p, 16)
                        word_offset = base_addr - 0x20000
                        for bi in range(4):
                            byte_abs = word_offset + bi
                            row = byte_abs // FB_STRIDE
                            col = byte_abs % FB_STRIDE
                            if row < FB_H and col < FB_W:
                                fb[row * FB_W + col] = (word_val >> (bi * 8)) & 0xFF
                        base_addr += 4
                    else:
                        break
    # Parse debug word
    dw = 0
    m = debug_word_re.search(r.stdout)
    if m:
        dw = int(m.group(1), 16)

    return bytes(fb), dw


def fb_to_ppm(fb: bytes, path: str):
    """Write a PPM P6 image from extracted framebuffer bytes (FB_W × FB_H = 300)."""
    scale = 24
    w, h = FB_W * scale, FB_H * scale
    with open(path, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode())
        for y in range(h):
            sy = y // scale
            for x in range(w):
                sx = x // scale
                p = fb[sy * FB_W + sx]
                f.write(bytes([p, p, p]))


def render_ppm(cycles: int, key: int = 0, label: str = "") -> dict:
    fb, dw = run_squash(cycles, key)
    state = decode_debug_word(dw)
    key_name = {0: "nokey", ord('w'): "wkey", ord('s'): "skey"}.get(key, f"key{key}")
    ppm_name = f"squash_{key_name}_{cycles}{label}.ppm"
    fb_to_ppm(fb, ppm_name)
    print(f"Wrote {ppm_name}")
    print(f"  Debug: {state}")
    return state


def main():
    import sys
    import multiprocessing

    # Build targets
    subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "squash_elf",
         "--", f"-j{multiprocessing.cpu_count()}"],
        cwd=EMULATOR_DIR, check=True, capture_output=True, timeout=300,
    )

    # Render frames at key moments
    frames = [
        (0, 0, ""),
        (50000, 0, ""),
        (100000, 0, ""),
        (150000, 0, ""),
        (200000, 0, ""),
        (500000, 0, ""),
        (10000000, 0, "_end"),
        # With keys at 10M cycles
        (10000000, ord('w'), "_w"),
        (10000000, ord('s'), "_s"),
    ]

    for cycles, key, label in frames:
        render_ppm(cycles, key, label)

    print("\nDone. Open the .ppm files to view (e.g. 'feh *.ppm')")


if __name__ == "__main__":
    main()
