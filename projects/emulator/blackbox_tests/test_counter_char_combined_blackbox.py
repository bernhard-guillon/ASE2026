#!/usr/bin/env python3
"""
Blackbox test for the combined counter-chargen model.

Verifies that:
- The first frame matches the neural reference glyph for input 65 ('A')
- The counter advances to 66 ('B') after that first frame
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neural_reference import NeuralNetworkReference


def _run(elf: Path, cycles: int) -> tuple[list[int], int]:
    emulator = elf.parent / "emulator_runner"
    result = subprocess.run(
        [str(emulator), str(elf), "--char-code", "65", "--cycles", str(cycles), "--dump-framebuffer", "--dump-memory", "0x153FE0", "4"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"Run failed for {elf.name}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    fb_line = next((ln for ln in result.stdout.splitlines() if ln.startswith("FRAMEBUFFER_HEX:")), None)
    assert fb_line is not None, "Missing framebuffer dump"
    fb_hex = fb_line[len("FRAMEBUFFER_HEX:"):].strip()
    framebuffer = [int(fb_hex[i : i + 2], 16) for i in range(0, len(fb_hex), 2)]

    debug_line = next((ln for ln in result.stdout.splitlines() if ln.startswith("0x00153fe0:")), None)
    assert debug_line is not None, "Missing debug word dump"
    debug_word = int(debug_line.split()[1], 16)

    return framebuffer, debug_word


def main() -> int:
    build = Path(__file__).parent.parent / "build"
    combined = build / "counter-char-combined.elf"
    assert combined.exists(), f"Missing ELF: {combined}"

    ref = NeuralNetworkReference(str(Path(__file__).resolve().parents[2] / "weight-export" / "character_generator.json"))
    inputs_a = np.zeros(255, dtype=np.float32)
    inputs_a[65] = 1.0
    ref_a = (ref.forward_pass(inputs_a) >= 0.5).astype(np.uint8).tolist()

    fb, debug_word = _run(combined, 5_000_000)
    diff = sum(1 for a, b in zip(fb, ref_a) if (1 if b else 0) != (1 if a >= 200 else 0))

    if diff > 40:
        print(f"First frame is too far from the neural A glyph (diff={diff})")
        return 1

    if debug_word != 66:
        print(f"Counter did not advance to B: got {debug_word}")
        return 1

    print("✓ First frame matches neural A glyph closely")
    print("✓ Counter advances to B after the frame")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
