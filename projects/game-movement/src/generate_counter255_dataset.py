"""
Generate exhaustive modulo-255 counter dataset.

Input and output are one-hot vectors of length 255:
- x[n] = onehot(n)
- y[n] = onehot((n+1) % 255)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from counter255_oracle import COUNTER255_MODULUS, counter255_step


def _one_hot(index: int, size: int) -> np.ndarray:
    vec = np.zeros(size, dtype=np.float32)
    vec[index] = 1.0
    return vec


def generate_counter255_dataset(npz_path: str = "counter255_dataset.npz", json_path: str = "counter255_transitions.json") -> dict[str, np.ndarray]:
    x_rows = []
    y_rows = []
    transitions: list[dict[str, int]] = []

    for state in range(COUNTER255_MODULUS):
        next_state = counter255_step(state)
        x_rows.append(_one_hot(state, COUNTER255_MODULUS))
        y_rows.append(_one_hot(next_state, COUNTER255_MODULUS))
        transitions.append({"state": state, "next_state": next_state})

    x = np.stack(x_rows).astype(np.float32)
    y = np.stack(y_rows).astype(np.float32)

    np.savez(npz_path, x=x, y=y)
    Path(json_path).write_text(json.dumps(transitions, indent=2), encoding="utf-8")
    return {"x": x, "y": y}


if __name__ == "__main__":
    arrays = generate_counter255_dataset()
    print(f"Generated dataset: x={arrays['x'].shape}, y={arrays['y'].shape}")

