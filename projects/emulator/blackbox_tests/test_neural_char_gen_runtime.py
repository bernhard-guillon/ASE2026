#!/usr/bin/env python3
"""
Smoke test for neural char_gen runtime (C-based, Rust-compiled model).
Verifies the ELF loads and produces non-zero framebuffer output.
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
CHAR_GEN_ELF = BUILD_DIR / "char_gen.elf"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
FRAMEBUFFER_SIZE = 400


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-gcc") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "char_gen_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        f"Failed to build char_gen targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"emulator_runner missing: {RUNNER}"
    assert CHAR_GEN_ELF.exists(), f"char_gen.elf missing: {CHAR_GEN_ELF}"


def _run_char(char_code: int, cycles: int) -> list[int]:
    run = subprocess.run(
        [
            str(RUNNER),
            str(CHAR_GEN_ELF),
            "--char-code",
            str(char_code),
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
        f"char_gen runtime failed (char_code={char_code}, cycles={cycles}).\n"
        f"stdout:\n{run.stdout}\n"
        f"stderr:\n{run.stderr}"
    )
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{run.stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX):].strip()
    assert len(hex_data) == FRAMEBUFFER_SIZE * 2, f"Unexpected framebuffer length: {len(hex_data)}"
    return [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]


def test_char_gen_produces_framebuffer_output() -> None:
    _require_env()
    _build_targets()
    pixels = _run_char(65, 5_000_000)
    non_zero = [p for p in pixels if p != 0]
    assert len(non_zero) > 0, "Framebuffer is all zeros — model produced no output"


def test_char_gen_is_deterministic() -> None:
    _require_env()
    _build_targets()
    pixels_a = _run_char(65, 5_000_000)
    pixels_b = _run_char(65, 5_000_000)
    assert pixels_a == pixels_b, "Framebuffer output differs between identical runs"


def test_char_gen_different_chars_differ() -> None:
    _require_env()
    _build_targets()
    pixels_A = _run_char(65, 5_000_000)
    pixels_B = _run_char(66, 5_000_000)
    non_zero_A = [i for i, p in enumerate(pixels_A) if p != 0]
    non_zero_B = [i for i, p in enumerate(pixels_B) if p != 0]
    assert non_zero_A != non_zero_B, "Different characters produced identical framebuffer"
