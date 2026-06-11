#!/usr/bin/env python3
"""
Verilator smoke test for squash game runtime (Rust-compiled block-diagonal MLP).
Mirrors test_squash_runtime.py but runs on verilator_runner.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
RUNNER = BUILD_DIR / "verilator_runner"
SQUASH_ELF = BUILD_DIR / "squash.elf"

DEBUG_WORD_ADDR = "0x153fe0"
MEM_LINE_RE = re.compile(r":\s+0x([0-9a-f]+)\s+\(")


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-gcc", "verilator") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    import multiprocessing
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "verilator_runner", "squash_elf", "--", f"-j{multiprocessing.cpu_count()}"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, (
        f"Failed to build verilator+squash targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"verilator_runner missing: {RUNNER}"
    assert SQUASH_ELF.exists(), f"squash.elf missing: {SQUASH_ELF}"


def _run(a0_val: int, cycles: int) -> int:
    cmd = [str(RUNNER), str(SQUASH_ELF)]
    if a0_val != 0:
        cmd += ["--char-code", str(a0_val)]
    cmd += ["--cycles", str(cycles), "--dump-memory", DEBUG_WORD_ADDR, "1"]
    run = subprocess.run(cmd,
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # Verify there was no crash (stdout should have the dump line)
    assert "0x" + DEBUG_WORD_ADDR[2:] in run.stdout, (
        f"Missing debug word in output.\nstdout:\n{run.stdout}\n"
        f"stderr:\n{run.stderr}"
    )
    match = MEM_LINE_RE.search(run.stdout)
    assert match is not None, f"Could not parse debug word.\nstdout:\n{run.stdout}"
    return int(match.group(1), 16)


def _parse_debug_word(val: int) -> dict:
    ball_vy = val & 1
    ball_vx = (val >> 1) & 1
    rest = val - (ball_vx * 2 + ball_vy)
    rest //= 10
    game_state = rest % 10
    rest //= 10
    paddle_y = None
    ball_y_val = None
    ball_x_val = None
    for bx_candidate in range(20):
        bx_part = bx_candidate * 100
        if bx_part > rest:
            break
        remaining = rest - bx_part
        by_candidate = remaining // 10
        py_candidate = remaining % 10
        if by_candidate < 15 and py_candidate < 11:
            ball_x_val = bx_candidate
            ball_y_val = by_candidate
            paddle_y = py_candidate
            break
    if ball_x_val is None:
        ball_x_val = ball_y_val = paddle_y = 0xFFFFFFFF
    return {
        "ball_x": ball_x_val,
        "ball_y": ball_y_val,
        "paddle_y": paddle_y,
        "game_state": game_state,
        "ball_vx": ball_vx,
        "ball_vy": ball_vy,
    }


def test_verilator_squash_deterministic() -> None:
    """Same input + same cycles = same state."""
    _require_env()
    _build_targets()
    s1 = _run(0, 2_000_000)
    s2 = _run(0, 2_000_000)
    assert s1 == s2


def test_verilator_squash_progresses() -> None:
    """Ball/paddle state changes between early cycles."""
    _require_env()
    _build_targets()
    s1 = _run(0, 2_000_000)
    s2 = _run(0, 4_000_000)
    assert s1 != s2, "State should change between 2M and 4M cycles"


def test_verilator_squash_key_changes_state() -> None:
    """Pressing a key should change game state (paddle position).

    Key is injected via memory-mapped register at 0x154004 (not forced a0),
    so normal register usage is preserved.
    """
    _require_env()
    _build_targets()
    no_key = _parse_debug_word(_run(0, 2_000_000))
    w_key = _parse_debug_word(_run(ord('w'), 2_000_000))
    assert w_key["paddle_y"] != no_key["paddle_y"], \
        f"Expected paddle_y to change with 'w', got {w_key['paddle_y']}"
