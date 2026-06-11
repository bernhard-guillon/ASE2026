#!/usr/bin/env python3
"""
Verilator squash game key input test.
Verifies that paddle movement (w/s keys) produces the same game state
on verilator as on emulator, using --char-code for deterministic comparison.
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
DEBUG_WORD_ADDR = "0x153fe0"
MEM_LINE_RE = re.compile(r"0x00153fe0:\s+0x([0-9a-fA-F]+)")


def _require_env() -> None:
    missing = [t for t in ("cmake", "riscv64-elf-gcc", "verilator") if shutil.which(t) is None]
    if missing:
        pytest.skip(f"Missing toolchain ({', '.join(missing)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    import multiprocessing
    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target",
         "verilator_runner", "emulator_runner", "squash_elf",
         "--", f"-j{multiprocessing.cpu_count()}"],
        cwd=EMULATOR_DIR,
        capture_output=True, text=True, timeout=600,
    )
    assert build.returncode == 0, (
        f"Failed to build targets.\nstdout:\n{build.stdout}\nstderr:\n{build.stderr}")


def _run(runner: Path, char_code: int, cycles: int) -> int:
    cmd = [str(runner), str(BUILD_DIR / "squash.elf"),
           "--char-code", str(char_code),
           "--cycles", str(cycles),
           "--dump-memory", DEBUG_WORD_ADDR, "1"]
    res = subprocess.run(cmd, cwd=EMULATOR_DIR, capture_output=True,
                         text=True, timeout=300)
    for line in res.stdout.splitlines():
        m = MEM_LINE_RE.search(line)
        if m:
            return int(m.group(1), 16)
    pytest.fail(f"Debug word not found.\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}")


def _decode_debug(val: int) -> dict:
    ball_vy = val & 1
    ball_vx = (val >> 1) & 1
    rest = val - (ball_vx * 2 + ball_vy)
    rest //= 10
    game_state = rest % 10
    rest //= 10
    paddle_y = rest % 10
    ball_y = (rest // 10) % 1000
    ball_x = rest // 10000
    return dict(ball_x=ball_x, ball_y=ball_y, paddle_y=paddle_y,
                game_state=game_state, ball_vx=ball_vx, ball_vy=ball_vy)


def _compare_emu_vlt(char_code: int, cycles_emu: int, cycles_vlt: int) -> None:
    emu_val = _run(BUILD_DIR / "emulator_runner", char_code, cycles_emu)
    vlt_val = _run(BUILD_DIR / "verilator_runner", char_code, cycles_vlt)
    emu = _decode_debug(emu_val)
    vlt = _decode_debug(vlt_val)
    for key in ("ball_x", "ball_y", "paddle_y", "game_state"):
        assert emu[key] == vlt[key], (
            f"char_code={char_code} key={key}: emu={emu[key]} vlt={vlt[key]}\n"
            f"emu full: {emu}\nvlt full: {vlt}")


class TestSquashKeyInput:
    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_env()
        _build_targets()

    def test_no_key_same_state(self):
        """Both runners produce same game state without key input."""
        _compare_emu_vlt(0, 25000, 1000000)

    def test_w_key_paddle_moves_up(self):
        """'w' key moves paddle up (paddle_y decreases)."""
        emu_val = _run(BUILD_DIR / "emulator_runner", ord("w"), 25000)
        vlt_val = _run(BUILD_DIR / "verilator_runner", ord("w"), 1000000)
        emu = _decode_debug(emu_val)
        vlt = _decode_debug(vlt_val)
        assert emu["paddle_y"] < 3, f"Expected paddle_y < 3 with 'w', got emu={emu['paddle_y']}"
        assert vlt["paddle_y"] < 3, f"Expected paddle_y < 3 with 'w', got vlt={vlt['paddle_y']}"
        assert emu["paddle_y"] == vlt["paddle_y"], (
            f"Paddle mismatch: emu={emu['paddle_y']} vlt={vlt['paddle_y']}")

    def test_s_key_paddle_moves_down(self):
        """'s' key moves paddle down (paddle_y increases)."""
        emu_val = _run(BUILD_DIR / "emulator_runner", ord("s"), 25000)
        vlt_val = _run(BUILD_DIR / "verilator_runner", ord("s"), 1000000)
        emu = _decode_debug(emu_val)
        vlt = _decode_debug(vlt_val)
        assert emu["paddle_y"] > 3, f"Expected paddle_y > 3 with 's', got emu={emu['paddle_y']}"
        assert vlt["paddle_y"] > 3, f"Expected paddle_y > 3 with 's', got vlt={vlt['paddle_y']}"
        assert emu["paddle_y"] == vlt["paddle_y"], (
            f"Paddle mismatch: emu={emu['paddle_y']} vlt={vlt['paddle_y']}")

    def test_key_changes_state(self):
        """Different keys produce different paddle positions."""
        none_val = _run(BUILD_DIR / "verilator_runner", 0, 1000000)
        w_val = _run(BUILD_DIR / "verilator_runner", ord("w"), 1000000)
        s_val = _run(BUILD_DIR / "verilator_runner", ord("s"), 1000000)
        none = _decode_debug(none_val)
        w = _decode_debug(w_val)
        s = _decode_debug(s_val)
        assert none["paddle_y"] != w["paddle_y"], "No-key and 'w' should differ"
        assert none["paddle_y"] != s["paddle_y"], "No-key and 's' should differ"
        assert w["paddle_y"] < none["paddle_y"], "'w' paddle should be higher (lower y)"
        assert s["paddle_y"] > none["paddle_y"], "'s' paddle should be lower (higher y)"

    def test_ball_moves(self):
        """Ball position changes across multiple inferences."""
        v1 = _run(BUILD_DIR / "verilator_runner", 0, 1000000)
        v2 = _run(BUILD_DIR / "verilator_runner", 0, 4000000)
        d1 = _decode_debug(v1)
        d2 = _decode_debug(v2)
        assert d1["ball_x"] != d2["ball_x"] or d1["ball_y"] != d2["ball_y"], (
            f"Ball should move: v1={d1} v2={d2}")
