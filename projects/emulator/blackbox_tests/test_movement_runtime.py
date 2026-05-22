#!/usr/bin/env python3
"""
Smoke test for neural movement runtime (C-based, Rust-compiled model).
Verifies the ELF loads, produces a single active pixel, and responds to input.
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
MOVEMENT_ELF = BUILD_DIR / "movement.elf"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
BOARD_CELLS = 400
BOARD_SIZE = 20


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-gcc") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "movement_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        f"Failed to build movement targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"emulator_runner missing: {RUNNER}"
    assert MOVEMENT_ELF.exists(), f"movement.elf missing: {MOVEMENT_ELF}"


def _run(a0_val: int, cycles: int) -> list[int]:
    run = subprocess.run(
        [
            str(RUNNER),
            str(MOVEMENT_ELF),
            "--char-code",
            str(a0_val),
            "--cycles",
            str(cycles),
            "--dump-framebuffer",
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, (
        f"movement runtime failed (a0={a0_val}, cycles={cycles}).\n"
        f"stdout:\n{run.stdout}\n"
        f"stderr:\n{run.stderr}"
    )
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{run.stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX):].strip()
    assert len(hex_data) == BOARD_CELLS * 2, f"Unexpected framebuffer length: {len(hex_data)}"
    return [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]


def _active_cell(pixels: list[int]) -> int:
    active = [i for i, p in enumerate(pixels) if p != 0]
    assert len(active) == 1, f"Expected exactly one active cell, got {len(active)}"
    return active[0]


def test_movement_initial_state() -> None:
    """With no keypress (a0=0), defaults to action=stay at position 200."""
    _require_env()
    _build_targets()
    pixels = _run(0, 500_000)
    cell = _active_cell(pixels)
    assert cell == 200, f"Expected initial cell 200, got {cell}"


def test_movement_deterministic() -> None:
    """Same input produces same output."""
    _require_env()
    _build_targets()
    p1 = _run(0, 500_000)
    p2 = _run(0, 500_000)
    assert p1 == p2


def test_movement_responds_to_keypress() -> None:
    """Pressing 'k' (up, ASCII 107) from state 200 produces a different cell."""
    _require_env()
    _build_targets()
    pixels = _run(107, 500_000)
    cell = _active_cell(pixels)
    assert cell != 200, "Model did not move despite 'k' (up) keypress"
    assert 0 <= cell < BOARD_CELLS, f"Cell out of range: {cell}"
