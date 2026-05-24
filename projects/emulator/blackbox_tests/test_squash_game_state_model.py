"""
Test exported squash game state model against reference physics.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
EMULATOR_DIR = REPO_ROOT / "projects" / "emulator"
BUILD_DIR = EMULATOR_DIR / "build"

sys.path.insert(0, str(EMULATOR_DIR / "training"))
sys.path.insert(0, str(EMULATOR_DIR))

from squash_physics import (
    INPUT_SIZE, OUTPUT_SIZE,
    BALL_X_RANGE, BALL_Y_RANGE, BALL_V_RANGE,
    PADDLE_Y_RANGE, GAME_STATE_RANGE, KEY_RANGE,
    generate_all_game_state_samples, squash_physics,
    encode_input, encode_output,
)
from neural_reference import NeuralNetworkReference


def _get_model_path():
    path = BUILD_DIR / "squash_game_state.json"
    if not path.exists():
        pytest.skip(f"Game state model not found: {path}")
    return str(path)


def test_game_state_model_exists():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)
    assert ref.metadata["model_type"] == "squash_game_state"


def test_game_state_model_all_samples():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)

    errors = 0
    total = 0
    groups = [
        (0, BALL_X_RANGE, "bx"),
        (BALL_X_RANGE, BALL_Y_RANGE, "by"),
        (BALL_X_RANGE + BALL_Y_RANGE, PADDLE_Y_RANGE, "py"),
        (BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE, GAME_STATE_RANGE, "gs"),
    ]

    for inp, expected_out in generate_all_game_state_samples():
        out = ref.forward_pass(np.array(inp, dtype=np.float32), use_piecewise=True)
        # Use "none" activation for output layer — raw logits
        # (model was trained with softmax CE, output activation="none")
        total += 1
        match = True
        for start, size, name in groups:
            if out[start:start+size].argmax() != np.array(expected_out[start:start+size]).argmax():
                match = False
                break
        if not match:
            errors += 1
            if errors <= 3:
                for start, size, name in groups:
                    pv = out[start:start+size].argmax()
                    ev = np.array(expected_out[start:start+size]).argmax()
                    if pv != ev:
                        print(f"  {name}: pred={pv} exp={ev}")

    acc = 1.0 - errors / total
    print(f"Game state model: {acc*100:.2f}% argmax accuracy ({total-errors}/{total})")
    assert acc == 1.0, f"Model has {errors}/{total} argmax errors"


def test_game_state_model_deterministic():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)

    inp = encode_input(10, 7, 1, 0, 3, 0, 0, 0)
    out1 = ref.forward_pass(np.array(inp, dtype=np.float32))
    out2 = ref.forward_pass(np.array(inp, dtype=np.float32))
    np.testing.assert_array_equal(out1, out2)


import pytest  # noqa: E402 (needed for pytest.skip)
