#!/usr/bin/env python3
"""Blackbox tests for custom neural instruction assembler encodings."""

from __future__ import annotations

import os
import struct
import subprocess
import tempfile
import shutil
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASM_ROOT = REPO_ROOT / "blackbox_tests" / "neural_instr_asm"


def _rv32as_path() -> Path:
    override = os.environ.get("EMULATOR_NEW_ASSEMBLER")
    if override:
        return Path(override)
    return REPO_ROOT / "build" / "rv32as"


def _assemble_and_extract_word(asm_file: Path) -> int:
    rv32as = _rv32as_path()
    assert rv32as.exists(), f"rv32as not found at {rv32as}"

    objcopy = shutil.which("riscv64-elf-objcopy") or shutil.which("riscv64-unknown-elf-objcopy")
    if objcopy is None:
        pytest.skip("RISC-V objcopy not found")

    with tempfile.TemporaryDirectory(prefix="neural_instr_asm_") as td:
        obj_file = Path(td) / "test.o"
        text_bin = Path(td) / "test.text.bin"

        result = subprocess.run(
            [str(rv32as), str(asm_file), "-o", str(obj_file)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"assembly failed for {asm_file.name}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

        result = subprocess.run(
            [objcopy, "-O", "binary", "-j", ".text", str(obj_file), str(text_bin)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"objcopy failed for {asm_file.name}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        data = text_bin.read_bytes()
        assert len(data) == 4, f"expected single instruction in {asm_file.name}, got {len(data)} bytes"
        return struct.unpack("<I", data)[0]


def _expected_word(opid: int, rd: int, rs1: int, rs2: int, rs3: int, opcode: int) -> int:
    return ((opid & 0x1F) << 27) | ((rs3 & 0x1F) << 22) | ((rs2 & 0x1F) << 17) | ((rs1 & 0x1F) << 12) | ((rd & 0x1F) << 7) | opcode


def test_nmatvec_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nmatvec" / "test.s")
    assert word == _expected_word(0, 6, 5, 0, 0, 0x77)


def test_nvrelu_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvrelu" / "test.s")
    assert word == _expected_word(1, 10, 11, 12, 13, 0x77)


def test_nvsigpwl_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvsigpwl" / "test.s")
    assert word == _expected_word(2, 5, 18, 19, 20, 0x77)


def test_nvclampu8_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvclampu8" / "test.s")
    assert word == _expected_word(3, 8, 10, 11, 12, 0x77)


def test_nmatvecx_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nmatvecx" / "test.s")
    assert word == _expected_word(0, 6, 5, 0, 0, 0x7B)


def test_nmatvec4x_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nmatvec4x" / "test.s")
    assert word == _expected_word(4, 6, 5, 0, 0, 0x7B)


def test_nmatvec8x_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nmatvec8x" / "test.s")
    assert word == _expected_word(5, 6, 5, 0, 0, 0x7B)


def test_nmatvec8xp_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nmatvec8xp" / "test.s")
    assert word == _expected_word(6, 6, 5, 0, 0, 0x7B)


def test_nvrelux_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvrelux" / "test.s")
    assert word == _expected_word(1, 10, 11, 12, 13, 0x7B)


def test_nvsigpwlx_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvsigpwlx" / "test.s")
    assert word == _expected_word(2, 5, 18, 19, 20, 0x7B)


def test_nvclampu8x_encoding():
    word = _assemble_and_extract_word(ASM_ROOT / "nvclampu8x" / "test.s")
    assert word == _expected_word(3, 8, 10, 11, 12, 0x7B)
