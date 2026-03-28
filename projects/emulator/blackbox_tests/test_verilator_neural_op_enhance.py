#!/usr/bin/env python3
"""Verify Verilator backend executes neural-op-enhance.elf correctly."""

from __future__ import annotations

import subprocess
import re
import os
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


def test_verilator_neural_op_enhance_runs_and_matches_cpp():
    emulator_dir = Path(__file__).parent.parent
    build_dir = emulator_dir / "build"
    cpp_runner = build_dir / "emulator_runner"
    verilator_runner = build_dir / "verilator_runner"
    assert cpp_runner.exists(), f"Missing emulator runner: {cpp_runner}"
    assert verilator_runner.exists(), f"Missing verilator runner: {verilator_runner}"
    variant_map = {
        "base": "neural-op-enhance.elf",
        "4x": "neural-op-enhance4.elf",
        "8x": "neural-op-enhance8.elf",
        "8xpmac": "neural-op-enhance8pmac.elf",
    }
    variants_env = os.environ.get("NEURAL_ENHANCE_VARIANTS", "base").strip()
    variants = [v.strip() for v in variants_env.split(",") if v.strip()]
    assert variants, "NEURAL_ENHANCE_VARIANTS resolved to empty list"

    cpp_cycles = 20_000
    verilator_cycles = 5_000_000
    cases = [65, 122]  # A, z

    for variant in variants:
        assert variant in variant_map, f"Unsupported NEURAL_ENHANCE_VARIANTS entry: {variant}"
        elf = build_dir / variant_map[variant]
        assert elf.exists(), f"Missing neural op enhance ELF for variant {variant}: {elf}"

        for char_code in cases:
            cpp_res = _run(cpp_runner, elf, char_code, cpp_cycles)
            vlt_res = _run(verilator_runner, elf, char_code, verilator_cycles)

            assert cpp_res.returncode == 0, (
                f"cpp runner failed for variant={variant} char={char_code}\n"
                f"stdout:\n{cpp_res.stdout}\nstderr:\n{cpp_res.stderr}"
            )
            assert vlt_res.returncode == 0, (
                f"verilator runner failed for variant={variant} char={char_code}\n"
                f"stdout:\n{vlt_res.stdout}\nstderr:\n{vlt_res.stderr}"
            )

            cpp_grid = _extract_grid(cpp_res.stdout)
            vlt_grid = _extract_grid(vlt_res.stdout)
            assert cpp_grid is not None, f"cpp framebuffer missing for variant={variant} char={char_code}"
            assert vlt_grid is not None, f"verilator framebuffer missing for variant={variant} char={char_code}"
            assert cpp_grid == vlt_grid, (
                f"framebuffer mismatch for variant={variant} char={char_code}\n"
                f"CPP:\n{cpp_grid}\n\nVLT:\n{vlt_grid}"
            )
