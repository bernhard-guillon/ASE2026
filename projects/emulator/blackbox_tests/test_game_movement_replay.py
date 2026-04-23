#!/usr/bin/env python3
"""
Replay movement corpus samples through emulator using packed-a0 movement mapping.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
GAME_MOVEMENT_DIR = REPO_ROOT / "projects" / "game-movement" / "src"

MODEL_JSON = GAME_MOVEMENT_DIR / "movement_generator.json"
TRANSITIONS_JSON = GAME_MOVEMENT_DIR / "movement_transitions.json"
INTERACTIVE_COMPILER = EMULATOR_DIR / "model_compiler_interactive.py"
RUNNER = EMULATOR_DIR / "build" / "emulator_runner"
RV32AS = EMULATOR_DIR / "build" / "rv32as"
LINKER_SCRIPT = EMULATOR_DIR / "linker.ld"

FRAMEBUFFER_PREFIX = "FRAMEBUFFER_HEX:"
FRAMEBUFFER_SIZE = 400
REPLAY_CYCLES = 5_000_000


def _pack_a0(state_index: int, action_id: int) -> int:
    return int(state_index) | (int(action_id) << 9)


def _parse_framebuffer_index(stdout: str) -> int:
    line = next((ln for ln in stdout.splitlines() if ln.startswith(FRAMEBUFFER_PREFIX)), None)
    assert line is not None, f"Missing framebuffer dump.\nstdout:\n{stdout}"
    hex_data = line[len(FRAMEBUFFER_PREFIX) :].strip()
    assert len(hex_data) == FRAMEBUFFER_SIZE * 2, f"Unexpected framebuffer dump length: {len(hex_data)}"
    pixels = [int(hex_data[i : i + 2], 16) for i in range(0, len(hex_data), 2)]
    active = [idx for idx, px in enumerate(pixels) if px != 0]
    assert len(active) == 1, f"Expected exactly one active cell, got {len(active)}"
    return active[0]


def _select_subset(samples: list[dict]) -> list[dict]:
    required_positions = {
        (0, 0), (19, 0), (0, 19), (19, 19),   # corners
        (10, 0), (10, 19), (0, 10), (19, 10), # edge centers
        (10, 10),                              # center
    }
    selected: list[dict] = []
    selected_keys: set[tuple[int, int, int]] = set()

    for sample in samples:
        key = (sample["x"], sample["y"], sample["action_id"])
        if (sample["x"], sample["y"]) in required_positions and key not in selected_keys:
            selected.append(sample)
            selected_keys.add(key)

    stride = 41
    for idx in range(0, len(samples), stride):
        sample = samples[idx]
        key = (sample["x"], sample["y"], sample["action_id"])
        if key not in selected_keys:
            selected.append(sample)
            selected_keys.add(key)
        if len(selected) >= 96:
            break

    return selected


def _require_env() -> None:
    missing_tools = [tool for tool in ("riscv64-elf-ld",) if shutil.which(tool) is None]
    if missing_tools:
        pytest.skip(f"Skipping movement replay test: missing toolchain ({', '.join(missing_tools)})")
    if not RV32AS.exists():
        pytest.skip(f"Skipping movement replay test: rv32as not found ({RV32AS})")
    if not LINKER_SCRIPT.exists():
        pytest.skip(f"Skipping movement replay test: linker script not found ({LINKER_SCRIPT})")
    if not RUNNER.exists():
        pytest.skip(f"Skipping movement replay test: emulator runner not found ({RUNNER})")
    if not MODEL_JSON.exists():
        pytest.skip(f"Skipping movement replay test: missing model JSON ({MODEL_JSON})")
    if not TRANSITIONS_JSON.exists():
        pytest.skip(f"Skipping movement replay test: missing transitions ({TRANSITIONS_JSON})")


@pytest.fixture(scope="module")
def compiled_movement_elf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    _require_env()
    out_dir = tmp_path_factory.mktemp("movement_replay")
    asm_path = out_dir / "movement_replay.s"
    obj_path = out_dir / "movement_replay.o"
    elf_path = out_dir / "movement_replay.elf"

    compile_result = subprocess.run(
        ["python3", str(INTERACTIVE_COMPILER), "-o", str(asm_path), str(MODEL_JSON)],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert compile_result.returncode == 0, (
        "Failed to generate interactive movement assembly.\n"
        f"stdout:\n{compile_result.stdout}\n"
        f"stderr:\n{compile_result.stderr}"
    )

    assemble_result = subprocess.run(
        [str(RV32AS), str(asm_path), "-march", "rv32if", "-mabi", "ilp32f", "-o", str(obj_path)],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert assemble_result.returncode == 0, (
        "Failed to assemble movement object.\n"
        f"stdout:\n{assemble_result.stdout}\n"
        f"stderr:\n{assemble_result.stderr}"
    )

    link_result = subprocess.run(
        ["riscv64-elf-ld", "-m", "elf32lriscv", "-T", str(LINKER_SCRIPT), "-o", str(elf_path), str(obj_path)],
        cwd=EMULATOR_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert link_result.returncode == 0, (
        "Failed to link movement ELF.\n"
        f"stdout:\n{link_result.stdout}\n"
        f"stderr:\n{link_result.stderr}"
    )
    assert elf_path.exists(), "Compiled ELF missing after successful pipeline run"
    return elf_path


def test_game_movement_replay_subset(compiled_movement_elf: Path) -> None:
    payload = json.loads(TRANSITIONS_JSON.read_text(encoding="utf-8"))
    samples = payload["samples"]
    replay_cases = _select_subset(samples)
    assert len(replay_cases) >= 50, "Replay subset unexpectedly small"

    for sample in replay_cases:
        packed_code = _pack_a0(sample["state_index"], sample["action_id"])
        cmd = [
            str(RUNNER),
            str(compiled_movement_elf),
            "--char-code",
            str(packed_code),
            "--cycles",
            str(REPLAY_CYCLES),
            "--dump-framebuffer",
        ]
        result = subprocess.run(
            cmd,
            cwd=EMULATOR_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Replay execution failed for state={sample['state_index']} action={sample['action_id']}.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        predicted_idx = _parse_framebuffer_index(result.stdout)
        expected_idx = int(sample["next_state_index"])
        assert predicted_idx == expected_idx, (
            "Replay mismatch: "
            f"state={sample['state_index']} action={sample['action_id']} ({sample['action']}) "
            f"expected={expected_idx}, got={predicted_idx}"
        )
