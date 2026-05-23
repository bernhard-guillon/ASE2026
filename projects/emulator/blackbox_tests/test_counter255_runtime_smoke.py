#!/usr/bin/env python3
"""
Smoke test for standalone counter255 runtime behavior.
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
RUNNER = BUILD_DIR / "emulator_runner"
COUNTER255_ELF = BUILD_DIR / "counter255.elf"

DEBUG_WORD_ADDR = 0x00153FE0
MEM_LINE_RE = re.compile(rf"^0x{DEBUG_WORD_ADDR:08x}:\s+0x([0-9a-fA-F]{{8}})")


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-ld") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Skipping counter255 runtime smoke test: missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Skipping counter255 runtime smoke test: build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "counter255_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        "Failed to build counter255 targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"Expected emulator_runner missing: {RUNNER}"
    assert COUNTER255_ELF.exists(), f"Expected counter255 ELF missing: {COUNTER255_ELF}"


def _run_and_read_counter(cycles: int) -> int:
    run = subprocess.run(
        [
            str(RUNNER),
            str(COUNTER255_ELF),
            "--cycles",
            str(cycles),
            "--dump-memory",
            hex(DEBUG_WORD_ADDR),
            "1",
        ],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert run.returncode == 0, (
        f"counter255 runtime failed (cycles={cycles}).\n"
        f"stdout:\n{run.stdout}\n"
        f"stderr:\n{run.stderr}"
    )
    value = None
    for line in run.stdout.splitlines():
        m = MEM_LINE_RE.match(line.strip())
        if m:
            value = int(m.group(1), 16)
            break
    assert value is not None, f"Could not read debug word from output.\nstdout:\n{run.stdout}"
    return value


def test_counter255_runtime_is_deterministic_and_progresses() -> None:
    _require_env()
    _build_targets()

    v2a = _run_and_read_counter(2_000_000)
    v2b = _run_and_read_counter(2_000_000)
    assert v2a == v2b, "Counter value should be deterministic for identical cycle budget"
    assert 0 <= v2a <= 254, f"Counter value out of range: {v2a}"

    v6 = _run_and_read_counter(6_000_000)
    v10 = _run_and_read_counter(10_000_000)
    assert len({v2a, v6, v10}) >= 2, "Counter value did not progress across larger cycle budgets"


FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"


def _run_and_read_framebuffer(cycles: int) -> list[int]:
    run = subprocess.run(
        [str(RUNNER), str(COUNTER255_ELF), "--cycles", str(cycles), "--dump-framebuffer"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert run.returncode == 0, f"counter255 failed (cycles={cycles}).\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{run.stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX):].strip()
    assert len(hex_data) == 800, f"Unexpected framebuffer length: {len(hex_data)}"
    return [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]


def test_counter255_produces_framebuffer_output() -> None:
    _require_env()
    _build_targets()
    pixels = _run_and_read_framebuffer(2_000_000)
    active = [i for i, p in enumerate(pixels) if p != 0]
    assert len(active) == 1, f"Expected exactly one active pixel, got {len(active)}: {active}"
    assert pixels[active[0]] == 255, f"Active pixel should have value 255, got {pixels[active[0]]}"
