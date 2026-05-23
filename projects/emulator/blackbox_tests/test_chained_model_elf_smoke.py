#!/usr/bin/env python3
"""
Smoke test for chained dual-model ELF framebuffer output.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
RUNNER = BUILD_DIR / "emulator_runner"

CHAINED_JSON = BUILD_DIR / "chained_generator.json"
CHAINED_ASM = BUILD_DIR / "chained-model.s"
CHAINED_BIN = BUILD_DIR / "chained-model.bin"
CHAINED_OBJ = BUILD_DIR / "chained-model.o"
CHAINED_ELF = BUILD_DIR / "chained-model.elf"
PHYSICS_CKPT = REPO_ROOT / "projects" / "game-movement" / "src" / "physics_model.pth"
COUNTER_CKPT = REPO_ROOT / "projects" / "game-movement" / "src" / "counter_model.pth"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
FRAMEBUFFER_SIZE = 400
SMOKE_CYCLES = 12_000_000


def _require_env() -> None:
    missing_tools = [
        tool
        for tool in ("cmake", "riscv64-elf-as", "riscv64-elf-ld")
        if shutil.which(tool) is None
    ]
    if missing_tools:
        pytest.skip(f"Skipping chained ELF smoke test: missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Skipping chained ELF smoke test: build directory not found ({BUILD_DIR})")
    if not PHYSICS_CKPT.exists() or not COUNTER_CKPT.exists():
        pytest.skip(
            "Skipping chained ELF smoke test: missing checkpoints "
            f"({PHYSICS_CKPT.name}, {COUNTER_CKPT.name})"
        )


def _parse_pixels(stdout: str) -> list[int]:
    line = next((ln for ln in stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX) :].strip()
    assert len(hex_data) == FRAMEBUFFER_SIZE * 2, f"Unexpected framebuffer dump length: {len(hex_data)}"
    return [int(hex_data[i : i + 2], 16) for i in range(0, len(hex_data), 2)]


def _run_or_skip_on_torch_missing(cmd: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 and "No module named 'torch'" in (result.stderr or ""):
        pytest.skip("Skipping chained ELF smoke test: torch not available in Python environment")
    return result


def _ensure_runner() -> None:
    build_result = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build_result.returncode == 0, (
        "Failed to build emulator_runner target.\n"
        f"stdout:\n{build_result.stdout}\n"
        f"stderr:\n{build_result.stderr}"
    )
    assert RUNNER.exists(), f"Expected emulator_runner missing: {RUNNER}"


def _build_chained_elf() -> None:
    export_result = _run_or_skip_on_torch_missing(
        [
            sys.executable,
            str(REPO_ROOT / "projects" / "game-movement" / "src" / "export_chained.py"),
            "--physics-checkpoint",
            str(PHYSICS_CKPT),
            "--counter-checkpoint",
            str(COUNTER_CKPT),
            "--output",
            str(CHAINED_JSON),
        ],
        cwd=EMULATOR_DIR,
    )
    assert export_result.returncode == 0, (
        "Failed to export chained JSON.\n"
        f"stdout:\n{export_result.stdout}\n"
        f"stderr:\n{export_result.stderr}"
    )

    compile_result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "projects" / "emulator" / "model_compiler_interactive.py"),
            str(CHAINED_JSON),
            "-o",
            str(CHAINED_ASM),
            "-b",
            str(CHAINED_BIN),
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert compile_result.returncode == 0, (
        "Failed to compile chained JSON to assembly.\n"
        f"stdout:\n{compile_result.stdout}\n"
        f"stderr:\n{compile_result.stderr}"
    )

    as_result = subprocess.run(
        [
            "riscv64-elf-as",
            "-march=rv32if",
            "-mabi=ilp32f",
            "-o",
            str(CHAINED_OBJ),
            str(CHAINED_ASM),
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert as_result.returncode == 0, (
        "Failed to assemble chained-model.s.\n"
        f"stdout:\n{as_result.stdout}\n"
        f"stderr:\n{as_result.stderr}"
    )

    ld_result = subprocess.run(
        [
            "riscv64-elf-ld",
            "-m",
            "elf32lriscv",
            "-T",
            str(REPO_ROOT / "projects" / "emulator" / "linker.ld"),
            "-o",
            str(CHAINED_ELF),
            str(CHAINED_OBJ),
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert ld_result.returncode == 0, (
        "Failed to link chained-model.elf.\n"
        f"stdout:\n{ld_result.stdout}\n"
        f"stderr:\n{ld_result.stderr}"
    )
    assert CHAINED_ELF.exists(), f"Expected built ELF missing: {CHAINED_ELF}"


def test_chained_model_elf_writes_ball_and_counter() -> None:
    _require_env()
    _ensure_runner()
    _build_chained_elf()

    run_result = subprocess.run(
        [
            str(RUNNER),
            str(CHAINED_ELF),
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
        "Chained ELF run failed.\n"
        f"stdout:\n{run_result.stdout}\n"
        f"stderr:\n{run_result.stderr}"
    )

    pixels = _parse_pixels(run_result.stdout)
    active = [idx for idx, value in enumerate(pixels) if value != 0]
    assert active, "Expected non-empty framebuffer for chained model"

    bottom_row = [pixels[380 + x] for x in range(20)]
    assert any(v != 0 for v in bottom_row), "Expected bottom-row counter visualization"

    non_bottom_active = [idx for idx in active if idx < 380]
    assert non_bottom_active, "Expected at least one non-bottom active pixel (ball visualization)"
