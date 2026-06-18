#!/usr/bin/env python3
"""
Verilator smoke test for block-diagonal combined counter+chargen model.
Mirrors test_counter_chargen_combined_smoke.py but runs on verilator_runner.
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
COMBINED_ELF = BUILD_DIR / "counter-chargen-combined.elf"

DEBUG_WORD_ADDR = 0x00153FE0
INITIAL_COUNTER = 97

MEM_LINE_RE = re.compile(rf"^0x{DEBUG_WORD_ADDR:08x}:\s+0x([0-9a-fA-F]{{8}})")
FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-gcc", "verilator") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    import multiprocessing
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "verilator_runner", "counter_chargen_combined_elf",
         "--", f"-j{multiprocessing.cpu_count()}"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, (
        f"Failed to build verilator+combined targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"verilator_runner missing: {RUNNER}"
    assert COMBINED_ELF.exists(), f"combined ELF missing: {COMBINED_ELF}"


def _run_and_read_counter(cycles: int) -> int:
    run = subprocess.run(
        [str(RUNNER), str(COMBINED_ELF), "--cycles", str(cycles), "--dump-memory", hex(DEBUG_WORD_ADDR), "1"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, f"combined failed (cycles={cycles}).\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    value = None
    for line in run.stdout.splitlines():
        m = MEM_LINE_RE.match(line.strip())
        if m:
            value = int(m.group(1), 16)
            break
    assert value is not None, f"Could not read debug word.\nstdout:\n{run.stdout}"
    return value


def _run_and_read_framebuffer(cycles: int) -> list[int]:
    run = subprocess.run(
        [str(RUNNER), str(COMBINED_ELF), "--cycles", str(cycles), "--dump-framebuffer"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, f"combined failed (cycles={cycles}).\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{run.stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX):].strip()
    assert len(hex_data) == 800, f"Unexpected framebuffer length: {len(hex_data)}"
    return [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]


def test_verilator_combined_counter_advances() -> None:
    """Counter starts at 97 ('a') and advances with more cycles (mod 255)."""
    _require_env()
    _build_targets()

    v6 = _run_and_read_counter(6_000_000)
    assert v6 != INITIAL_COUNTER, f"Counter should advance past {INITIAL_COUNTER}, got {v6}"

    v10 = _run_and_read_counter(10_000_000)
    assert v10 != v6, f"Counter should change with more cycles: {v6} -> {v10}"

    delta = (v10 - v6) % 255
    assert delta != 0, f"Counter wrapped to same value: {v6} -> {v10}"


def test_verilator_combined_is_deterministic() -> None:
    """Two runs at same cycle budget produce identical debug word."""
    _require_env()
    _build_targets()

    v1 = _run_and_read_counter(6_000_000)
    v2 = _run_and_read_counter(6_000_000)
    assert v1 == v2, "Counter value differs between identical runs"


def test_verilator_combined_produces_framebuffer_output() -> None:
    """Framebuffer contains non-zero pixels (character output)."""
    _require_env()
    _build_targets()

    pixels = _run_and_read_framebuffer(6_000_000)
    non_zero = [p for p in pixels if p != 0]
    assert len(non_zero) > 0, "Framebuffer is all zeros — no character output"


def test_verilator_combined_framebuffer_is_deterministic() -> None:
    """Framebuffer output is identical across identical runs."""
    _require_env()
    _build_targets()

    fb_a = _run_and_read_framebuffer(6_000_000)
    fb_b = _run_and_read_framebuffer(6_000_000)
    assert fb_a == fb_b, "Framebuffer differs between identical runs"


def test_verilator_combined_different_cycles_different_framebuffer() -> None:
    """Different cycle counts produce different character output."""
    _require_env()
    _build_targets()

    fb_6 = _run_and_read_framebuffer(6_000_000)
    fb_10 = _run_and_read_framebuffer(10_000_000)
    assert fb_6 != fb_10, "Framebuffer should differ between different cycle budgets"
