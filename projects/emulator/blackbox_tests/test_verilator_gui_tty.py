#!/usr/bin/env python3
"""
GUI TTY test: spawn emulator_runner and verilator_runner under a PTY,
inject keypresses, and capture ASCII framebuffer before/after to verify
paddle movement. Uses emulator output as the baseline metric.
"""

from __future__ import annotations

import os
import pty
import select
import signal
import subprocess
import time
from pathlib import Path
import shutil

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"
EMU_RUNNER = BUILD_DIR / "emulator_runner"
VLT_RUNNER = BUILD_DIR / "verilator_runner"
SQUASH_ELF = BUILD_DIR / "squash.elf"

FRAME_W = 20
FRAME_H_EMU = 20
FRAME_H_VLT = 15
FRAME_H_ACTIVE = 15
ESC = b"\x1b[2J\x1b[H"


def _require_env() -> None:
    missing = [t for t in ("cmake", "verilator") if shutil.which(t) is None]
    if missing:
        pytest.skip(f"Missing toolchain ({', '.join(missing)})")
    if not BUILD_DIR.exists():
        pytest.skip(f"Build directory not found ({BUILD_DIR})")


def _build_targets() -> None:
    import multiprocessing

    build = subprocess.run(
        ["cmake", "--build", str(BUILD_DIR), "--target",
         "verilator_runner", "emulator_runner", "squash_elf",
         "--", f"-j{multiprocessing.cpu_count()}"] ,
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, (
        f"Failed to build targets.\nstdout:\n{build.stdout}\nstderr:\n{build.stderr}")


class FrameReader:
    def __init__(self, master_fd: int, frame_h: int):
        self.master_fd = master_fd
        self.frame_h = frame_h
        self.buffer = b""
        self.raw = b""

    def _read_available(self, timeout: float = 0.1) -> bytes:
        ready, _, _ = select.select([self.master_fd], [], [], timeout)
        if not ready:
            return b""
        try:
            data = os.read(self.master_fd, 65536)
            if data:
                self.raw += data
            return data
        except OSError:
            return b""

    def _extract_frame(self) -> list[str] | None:
        idx = self.buffer.find(ESC)
        if idx == -1:
            # Keep tail to avoid unbounded growth.
            self.buffer = self.buffer[-4096:]
            return None
        self.buffer = self.buffer[idx + len(ESC):]
        while self.buffer.startswith(b"\r") or self.buffer.startswith(b"\n"):
            self.buffer = self.buffer[1:]

        lines: list[str] = []
        pos = 0
        for _ in range(self.frame_h):
            nl = self.buffer.find(b"\n", pos)
            if nl == -1:
                return None
            line = self.buffer[pos:nl]
            if line.endswith(b"\r"):
                line = line[:-1]
            lines.append(line.decode("ascii", errors="ignore"))
            pos = nl + 1
        self.buffer = self.buffer[pos:]
        return lines

    def read_frame(self, timeout: float = 5.0) -> list[str]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.buffer += self._read_available(0.1)
            frame = self._extract_frame()
            if frame is not None:
                return frame
        raise AssertionError("Timed out waiting for GUI frame")


def _normalize_frame(lines: list[str], frame_h: int) -> list[str]:
    out: list[str] = []
    for line in lines:
        if len(line) < FRAME_W:
            line = line.ljust(FRAME_W)
        out.append(line[:FRAME_W])
    return out[:frame_h]


def _paddle_top(lines: list[str], active_rows: int) -> int | None:
    lines = _normalize_frame(lines, active_rows)
    rows = []
    for y in range(1, active_rows - 1):
        if any(lines[y][x] == "#" for x in range(1, 4)):
            rows.append(y)
    if not rows:
        return None

    # Find longest contiguous run to avoid ball noise.
    best_run = []
    current = [rows[0]]
    for y in rows[1:]:
        if y == current[-1] + 1:
            current.append(y)
        else:
            if len(current) > len(best_run):
                best_run = current
            current = [y]
    if len(current) > len(best_run):
        best_run = current
    if len(best_run) < 3:
        return None
    return min(best_run)


def _frame_to_text(lines: list[str], frame_h: int) -> str:
    return "\n".join(_normalize_frame(lines, frame_h)) + "\n"


def _artifact_dir(tmp_path: Path) -> Path:
    env_dir = os.environ.get("GUI_TTY_ARTIFACT_DIR")
    if env_dir:
        out = Path(env_dir)
        out.mkdir(parents=True, exist_ok=True)
        return out
    return tmp_path


def _spawn_gui(runner: Path, extra_args: list[str]) -> tuple[subprocess.Popen[str], int]:
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        [str(runner), str(SQUASH_ELF), "--gui", "--gui-cycles", "50000", *extra_args],
        cwd=EMULATOR_DIR,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        text=False,
    )
    os.close(slave_fd)
    return proc, master_fd


def _shutdown(proc: subprocess.Popen[str], master_fd: int) -> None:
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass


def _capture_movement(
    runner: Path,
    frame_h: int,
    extra_args: list[str],
    label: str,
    key: bytes,
    expect_delta: int,
    tmp_path: Path,
) -> tuple[list[str], list[str], int, int]:
    proc, master_fd = _spawn_gui(runner, extra_args)
    reader = FrameReader(master_fd, frame_h)
    out_dir = _artifact_dir(tmp_path)
    try:
        before = None
        before_top = None
        for _ in range(10):
            frame = reader.read_frame(timeout=6.0)
            top = _paddle_top(frame, FRAME_H_ACTIVE)
            if top is not None:
                before = frame
                before_top = top
                break
        assert before is not None and before_top is not None, (
            f"Could not detect paddle in baseline frame ({label})")

        os.write(master_fd, key)

        after = None
        after_top = None
        deadline = time.time() + 8.0
        while time.time() < deadline:
            frame = reader.read_frame(timeout=2.0)
            top = _paddle_top(frame, FRAME_H_ACTIVE)
            if top is None:
                continue
            if expect_delta < 0 and top < before_top:
                after = frame
                after_top = top
                break
            if expect_delta > 0 and top > before_top:
                after = frame
                after_top = top
                break

        assert after is not None and after_top is not None, (
            f"Could not detect paddle movement ({label})")

        before_path = out_dir / f"frame_{label}_before.txt"
        after_path = out_dir / f"frame_{label}_after.txt"
        before_path.write_text(_frame_to_text(before, frame_h))
        after_path.write_text(_frame_to_text(after, frame_h))

        return before, after, before_top, after_top
    except Exception:
        raw_path = out_dir / f"frame_{label}_raw.txt"
        try:
            raw_path.write_bytes(reader.raw)
        except Exception:
            pass
        raise
    finally:
        _shutdown(proc, master_fd)


def test_gui_tty_emulator_baseline_and_verilator(tmp_path: Path) -> None:
    _require_env()
    _build_targets()
    if not EMU_RUNNER.exists() or not VLT_RUNNER.exists() or not SQUASH_ELF.exists():
        pytest.skip("Missing emulator_runner, verilator_runner, or squash.elf")

    _, _, emu_before_top, emu_after_top = _capture_movement(
        EMU_RUNNER,
        FRAME_H_EMU,
        [],
        "emu_s",
        b"s",
        1,
        tmp_path,
    )
    emu_delta = emu_after_top - emu_before_top
    assert emu_delta > 0, f"Emulator paddle did not move down (delta={emu_delta})"

    _, _, emu_before_top_w, emu_after_top_w = _capture_movement(
        EMU_RUNNER,
        FRAME_H_EMU,
        [],
        "emu_w",
        b"w",
        -1,
        tmp_path,
    )
    emu_delta_w = emu_after_top_w - emu_before_top_w
    assert emu_delta_w < 0, f"Emulator paddle did not move up (delta={emu_delta_w})"

    _, _, vlt_before_top, vlt_after_top = _capture_movement(
        VLT_RUNNER,
        FRAME_H_VLT,
        ["--gui-max-cycles", "500000"],
        "vlt_s",
        b"s",
        1,
        tmp_path,
    )
    vlt_delta = vlt_after_top - vlt_before_top

    _, _, vlt_before_top_w, vlt_after_top_w = _capture_movement(
        VLT_RUNNER,
        FRAME_H_VLT,
        ["--gui-max-cycles", "500000"],
        "vlt_w",
        b"w",
        -1,
        tmp_path,
    )
    vlt_delta_w = vlt_after_top_w - vlt_before_top_w

    assert vlt_delta > 0, (
        f"Verilator paddle did not move down. emu_delta={emu_delta} vlt_delta={vlt_delta}\n"
        f"emu_before={_artifact_dir(tmp_path) / 'frame_emu_s_before.txt'}\n"
        f"emu_after={_artifact_dir(tmp_path) / 'frame_emu_s_after.txt'}\n"
        f"vlt_before={_artifact_dir(tmp_path) / 'frame_vlt_s_before.txt'}\n"
        f"vlt_after={_artifact_dir(tmp_path) / 'frame_vlt_s_after.txt'}")

    assert vlt_delta_w < 0, (
        f"Verilator paddle did not move up. emu_delta={emu_delta_w} vlt_delta={vlt_delta_w}\n"
        f"emu_before={_artifact_dir(tmp_path) / 'frame_emu_w_before.txt'}\n"
        f"emu_after={_artifact_dir(tmp_path) / 'frame_emu_w_after.txt'}\n"
        f"vlt_before={_artifact_dir(tmp_path) / 'frame_vlt_w_before.txt'}\n"
        f"vlt_after={_artifact_dir(tmp_path) / 'frame_vlt_w_after.txt'}")
