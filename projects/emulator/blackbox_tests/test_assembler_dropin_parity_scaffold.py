#!/usr/bin/env python3
"""Scaffold for drop-in assembler parity testing.

This test is intentionally opt-in until the new assembler exists.
Set EMULATOR_NEW_ASSEMBLER to enable parity execution.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASM_ROOT = REPO_ROOT / "blackbox_tests" / "asm"


def _find_tool(*names: str) -> str | None:
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    return None


def _run(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def _extract_text_bytes(objcopy: str, obj_file: Path, out_file: Path, cwd: Path) -> bytes:
    _run([objcopy, "-O", "binary", "-j", ".text", str(obj_file), str(out_file)], cwd)
    return out_file.read_bytes()


def _first_word_mismatch(lhs: bytes, rhs: bytes) -> tuple[int, int, int] | None:
    limit = min(len(lhs), len(rhs)) // 4 * 4
    for i in range(0, limit, 4):
        a = int.from_bytes(lhs[i:i + 4], "little")
        b = int.from_bytes(rhs[i:i + 4], "little")
        if a != b:
            return (i // 4, a, b)
    if len(lhs) != len(rhs):
        return (limit // 4, -1, -1)
    return None


@pytest.mark.blackbox
def test_dropin_assembler_text_parity_scaffold():
    gnu_as = _find_tool("riscv64-elf-as", "riscv64-unknown-elf-as")
    objcopy = _find_tool("riscv64-elf-objcopy", "riscv64-unknown-elf-objcopy")

    if gnu_as is None or objcopy is None:
        pytest.skip("RISC-V GNU assembler/objcopy not available")

    new_assembler = os.environ.get("EMULATOR_NEW_ASSEMBLER")
    if not new_assembler:
        pytest.skip("Set EMULATOR_NEW_ASSEMBLER to enable drop-in assembler parity checks")

    new_assembler_path = Path(new_assembler)
    if not new_assembler_path.exists():
        pytest.fail(f"EMULATOR_NEW_ASSEMBLER does not exist: {new_assembler_path}")

    asm_files = sorted(ASM_ROOT.glob("**/test.s"))
    assert asm_files, f"No assembly corpus files found under {ASM_ROOT}"

    for asm_file in asm_files:
        with tempfile.TemporaryDirectory(prefix="as_parity_") as td:
            td_path = Path(td)
            gnu_obj = td_path / "gnu.o"
            new_obj = td_path / "new.o"
            gnu_bin = td_path / "gnu.text.bin"
            new_bin = td_path / "new.text.bin"

            _run([gnu_as, "-march=rv32if", "-mabi=ilp32f", "-o", str(gnu_obj), str(asm_file)], REPO_ROOT)
            _run([str(new_assembler_path), "-march=rv32if", "-mabi=ilp32f", "-o", str(new_obj), str(asm_file)], REPO_ROOT)

            gnu_text = _extract_text_bytes(objcopy, gnu_obj, gnu_bin, REPO_ROOT)
            new_text = _extract_text_bytes(objcopy, new_obj, new_bin, REPO_ROOT)

            mismatch = _first_word_mismatch(gnu_text, new_text)
            assert mismatch is None, (
                f".text mismatch for {asm_file.relative_to(REPO_ROOT)}; "
                f"first mismatch={mismatch}"
            )
