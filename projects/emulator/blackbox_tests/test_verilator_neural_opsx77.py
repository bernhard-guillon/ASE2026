#!/usr/bin/env python3
"""Verify Verilator backend executes neural-ai-opsx77.elf correctly."""

from __future__ import annotations

import subprocess
import re
from pathlib import Path


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _extract_grid(output: str):
    clean = ANSI_ESCAPE.sub("", output)
    lines = []
    for line in clean.splitlines():
        if len(line) == 20 and all(ch in " #█" for ch in line):
            lines.append(line.replace("█", "#"))
    if len(lines) < 20:
        return None
    return "\n".join(lines[:20])


def _run(runner: Path, elf: Path, char_code: int, cycles: int):
    return subprocess.run(
        [
            str(runner),
            str(elf),
            "--char-code",
            str(char_code),
            "--cycles",
            str(cycles),
            "--render-framebuffer",
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )


def test_verilator_neural_opsx77_runs_and_matches_cpp():
    emulator_dir = Path(__file__).parent.parent
    build_dir = emulator_dir / "build"
    cpp_runner = build_dir / "emulator_runner"
    verilator_runner = build_dir / "verilator_runner"
    neural_opsx77 = build_dir / "neural-ai-opsx77.elf"

    assert cpp_runner.exists(), f"Missing emulator runner: {cpp_runner}"
    assert verilator_runner.exists(), f"Missing verilator runner: {verilator_runner}"
    assert neural_opsx77.exists(), f"Missing neural opsx77 ELF: {neural_opsx77}"

    # HDL custom-op path is currently microcoded in CPU state machine and needs
    # substantially more cycles than emulator_runner's native C++ backend.
    cpp_cycles = 20_000
    verilator_cycles = 5_000_000

    # Use representative alphabetic cases and ensure identical framebuffer output.
    cases = [65, 122]  # A, z
    for char_code in cases:
        cpp_res = _run(cpp_runner, neural_opsx77, char_code, cpp_cycles)
        vlt_res = _run(verilator_runner, neural_opsx77, char_code, verilator_cycles)

        assert cpp_res.returncode == 0, (
            f"cpp runner failed for {char_code}\nstdout:\n{cpp_res.stdout}\nstderr:\n{cpp_res.stderr}"
        )
        assert vlt_res.returncode == 0, (
            f"verilator runner failed for {char_code}\nstdout:\n{vlt_res.stdout}\nstderr:\n{vlt_res.stderr}"
        )

        cpp_grid = _extract_grid(cpp_res.stdout)
        vlt_grid = _extract_grid(vlt_res.stdout)
        assert cpp_grid is not None, f"cpp framebuffer missing for char {char_code}"
        assert vlt_grid is not None, f"verilator framebuffer missing for char {char_code}"
        assert cpp_grid == vlt_grid, (
            f"framebuffer mismatch for char {char_code}\nCPP:\n{cpp_grid}\n\nVLT:\n{vlt_grid}"
        )
