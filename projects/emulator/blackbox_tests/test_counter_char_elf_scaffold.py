#!/usr/bin/env python3
"""
Phase-1 smoke test for counter->char scaffold ELF path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
RUNNER = BUILD_DIR / "emulator_runner"
ELF = BUILD_DIR / "counter-char.elf"
JSON_OUT = BUILD_DIR / "counter-char_generator.json"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
FRAMEBUFFER_SIZE = 400


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-ld") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Skipping counter-char scaffold smoke test: missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Skipping counter-char scaffold smoke test: build directory not found ({BUILD_DIR})")


def _parse_pixels(stdout: str) -> list[int]:
    line = next((ln for ln in stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX) :].strip()
    assert len(hex_data) == FRAMEBUFFER_SIZE * 2, f"Unexpected framebuffer dump length: {len(hex_data)}"
    return [int(hex_data[i : i + 2], 16) for i in range(0, len(hex_data), 2)]


def test_counter_char_scaffold_elf_builds_and_renders() -> None:
    _require_env()

    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "counter_char_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        "Failed to build counter_char_elf scaffold target.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"Expected emulator_runner missing: {RUNNER}"
    assert ELF.exists(), f"Expected counter-char ELF missing: {ELF}"
    assert JSON_OUT.exists(), f"Expected counter-char JSON missing: {JSON_OUT}"

    data = json.loads(JSON_OUT.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    assert metadata.get("counter_modulus") == 255
    assert metadata.get("counter_range") == [0, 254]
    assert metadata.get("bridge_register") == "a0"
    assert metadata.get("bridge_mapping") == "scalar_a0_to_onehot255"

    run_result = subprocess.run(
        [str(RUNNER), str(ELF), "--cycles", "12000000", "--dump-framebuffer"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run_result.returncode == 0, (
        "counter-char scaffold ELF run failed.\n"
        f"stdout:\n{run_result.stdout}\n"
        f"stderr:\n{run_result.stderr}"
    )
    pixels = _parse_pixels(run_result.stdout)
    assert any(v != 0 for v in pixels), "Expected non-empty framebuffer output for scaffold path"

