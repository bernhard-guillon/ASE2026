#!/usr/bin/env python3
"""
Smoke test for squash game-movement ELF framebuffer output.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
RUNNER = BUILD_DIR / "emulator_runner"
GAME_MOVEMENT_ELF = BUILD_DIR / "game-movement.elf"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
FRAMEBUFFER_SIZE = 400
SMOKE_CYCLES = 12_000_000
KEY_UP = 106  # ASCII 'j'


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-ld") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Skipping squash ELF smoke test: missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Skipping squash ELF smoke test: build directory not found ({BUILD_DIR})")
    if not RUNNER.exists():
        pytest.skip(f"Skipping squash ELF smoke test: emulator_runner not found ({RUNNER})")


def _parse_pixels(stdout: str) -> list[int]:
    line = next((ln for ln in stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX) :].strip()
    assert len(hex_data) == FRAMEBUFFER_SIZE * 2, f"Unexpected framebuffer dump length: {len(hex_data)}"
    return [int(hex_data[i : i + 2], 16) for i in range(0, len(hex_data), 2)]


def _ensure_game_movement_elf() -> None:
    build_result = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "game_movement_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build_result.returncode == 0, (
        "Failed to build game_movement_elf target.\n"
        f"stdout:\n{build_result.stdout}\n"
        f"stderr:\n{build_result.stderr}"
    )
    assert GAME_MOVEMENT_ELF.exists(), f"Expected built ELF missing: {GAME_MOVEMENT_ELF}"


def test_game_movement_elf_writes_visible_frame() -> None:
    _require_env()
    _ensure_game_movement_elf()

    run_result = subprocess.run(
        [
            str(RUNNER),
            str(GAME_MOVEMENT_ELF),
            "--char-code",
            str(KEY_UP),
            "--cycles",
            str(SMOKE_CYCLES),
            "--dump-framebuffer",
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run_result.returncode == 0, (
        "Squash ELF run failed.\n"
        f"stdout:\n{run_result.stdout}\n"
        f"stderr:\n{run_result.stderr}"
    )

    pixels = _parse_pixels(run_result.stdout)
    active = [idx for idx, value in enumerate(pixels) if value != 0]
    assert len(active) == 4, f"Expected 4 active cells from squash top-4 mapping, got {len(active)}"
    assert all(pixels[idx] == 255 for idx in active), "Active cells should be full-intensity (255)"

