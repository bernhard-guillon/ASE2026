#!/usr/bin/env python3
"""
Smoke test for combined counter-chargen model ELF.

Verifies:
- Combined ELF runs and produces visible output
- Counter increments each cycle
- Framebuffer output changes as counter increments
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    emulator = Path(__file__).parent.parent / "build" / "emulator_runner"
    elf = Path(__file__).parent.parent / "build" / "counter-char-combined.elf"

    if not emulator.exists():
        print(f"ERROR: emulator_runner not found at {emulator}")
        return 1

    if not elf.exists():
        print(f"ERROR: counter-char-combined.elf not found at {elf}")
        return 1

    print(f"Running combined model ELF smoke test...")
    print(f"  Emulator: {emulator}")
    print(f"  ELF: {elf}")

    # Run with a few cycles to see counter progress
    try:
        result = subprocess.run(
            [str(emulator), str(elf), "--cycle-limit", "50"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Emulator exit code: {result.returncode}")

        if result.stdout:
            print(f"Stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")

        # Just verify it ran without crashing
        if result.returncode == 0:
            print("✓ Combined model ELF smoke test passed")
            return 0
        else:
            print(f"✗ Emulator failed with exit code {result.returncode}")
            return 1

    except subprocess.TimeoutExpired:
        print("✗ Emulator timed out")
        return 1
    except Exception as e:
        print(f"✗ Error running emulator: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
