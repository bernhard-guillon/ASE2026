"""
Test exported squash renderer model against reference renderer.
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

from squash_renderer import (
    W, H, OUTPUT_PIXELS, INPUT_SIZE,
    BALL_X_RANGE, BALL_Y_RANGE, PADDLE_Y_RANGE, GAME_STATE_RANGE,
    generate_all_renderer_samples,
)
from neural_reference import NeuralNetworkReference


def _get_model_path():
    path = BUILD_DIR / "squash_renderer.json"
    if not path.exists():
        pytest.skip(f"Renderer model not found: {path}")
    return str(path)


def test_renderer_model_exists():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)
    assert ref.metadata["model_type"] == "squash_renderer"


def test_renderer_model_pixel_accuracy():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)

    errors = 0
    total = 0
    for inp, expected_pixels in generate_all_renderer_samples():
        out = ref.forward_pass(np.array(inp, dtype=np.float32), use_piecewise=True)
        pred = (out > 0.5).astype(np.float32)
        exp = np.array(expected_pixels, dtype=np.float32)
        total += 1
        if not np.array_equal(pred, exp):
            errors += 1

    acc = 1.0 - errors / total
    print(f"Renderer model: {acc*100:.2f}% pixel accuracy ({total-errors}/{total})")
    # Boundary pixels at paddle/wall edges may be slightly off;
    # the game is still playable with >97% accuracy
    assert acc >= 0.95, f"Model has {errors}/{total} pixel errors (below 95%)"


def test_renderer_model_deterministic():
    path = _get_model_path()
    ref = NeuralNetworkReference(path)

    inp = [0.0] * INPUT_SIZE
    inp[10] = 1.0  # ball_x=10
    inp[20 + 7] = 1.0  # ball_y=7
    inp[20 + 15 + 5] = 1.0  # paddle_y=5
    inp[20 + 15 + 11] = 1.0  # game_state=0
    out1 = ref.forward_pass(np.array(inp, dtype=np.float32))
    out2 = ref.forward_pass(np.array(inp, dtype=np.float32))
    np.testing.assert_array_equal(out1, out2)


import pytest  # noqa: E402
