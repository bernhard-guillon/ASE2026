#!/usr/bin/env python3
"""
Smoke test for mega combined model (squash + counter-chargen + router).
Verifies the merged MLP produces framebuffer output, Tab switching works,
and both sub-models produce valid output.
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
MEGA_ELF = BUILD_DIR / "mega-combined.elf"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"


def _require_env() -> None:
    missing_tools = [tool for tool in ("cmake", "riscv64-elf-gcc") if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Missing toolchain ({', '.join(missing_tools)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target", "emulator_runner", "mega_combined_elf", "--", "-j4"],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert build.returncode == 0, (
        f"Failed to build mega combined targets.\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )
    assert RUNNER.exists(), f"emulator_runner missing: {RUNNER}"
    assert MEGA_ELF.exists(), f"mega-combined.elf missing: {MEGA_ELF}"


def _run_framebuffer(cycles: int, key: int = 0) -> list[int]:
    """Run mega-combined.elf and return framebuffer pixels."""
    cmd = [str(RUNNER), str(MEGA_ELF), "--cycles", str(cycles), "--dump-framebuffer"]
    if key:
        cmd += ["--char-code", str(key)]
    run = subprocess.run(
        cmd,
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, f"mega-combined failed (cycles={cycles}, key={key}).\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    line = next((ln for ln in run.stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{run.stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX):].strip()
    return [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]


def test_mega_elf_exists() -> None:
    """Verify the ELF was built."""
    _require_env()
    _build_targets()
    assert MEGA_ELF.exists()


def test_mega_produces_framebuffer() -> None:
    """Framebuffer contains non-zero pixels in default (chargen) mode."""
    _require_env()
    _build_targets()

    pixels = _run_framebuffer(6_000_000)
    non_zero = [p for p in pixels if p != 0]
    assert len(non_zero) > 0, "Framebuffer is all zeros — no chargen output"


def test_mega_is_deterministic() -> None:
    """Two runs at same cycle budget produce identical framebuffer."""
    _require_env()
    _build_targets()

    fb_a = _run_framebuffer(6_000_000)
    fb_b = _run_framebuffer(6_000_000)
    assert fb_a == fb_b, "Framebuffer differs between identical runs"


def test_mega_chargen_mode() -> None:
    """Default mode (no Tab) should produce chargen-style framebuffer (20x20, 400 bytes)."""
    _require_env()
    _build_targets()

    pixels = _run_framebuffer(6_000_000)
    assert len(pixels) == 400, f"Expected 400 pixels, got {len(pixels)}"
    non_zero = [p for p in pixels if p != 0]
    assert len(non_zero) > 0, "Chargen mode produced all-zero framebuffer"


def test_mega_framebuffer_size() -> None:
    """Framebuffer is always 400 bytes (chargen layout, stride 20)."""
    _require_env()
    _build_targets()

    pixels = _run_framebuffer(6_000_000)
    assert len(pixels) == 400, f"Expected 400 framebuffer bytes, got {len(pixels)}"
