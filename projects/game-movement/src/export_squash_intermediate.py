"""
Export squash_model.pth to emulator JSON intermediate format.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from squash_model import SquashWorldModel


def _layer_to_dict(name: str, layer: torch.nn.Linear, activation: str) -> dict[str, Any]:
    weights = layer.weight.detach().cpu().numpy().astype(np.float32).T
    biases = layer.bias.detach().cpu().numpy().astype(np.float32)
    return {
        "name": name,
        "input_size": int(weights.shape[0]),
        "output_size": int(weights.shape[1]),
        "activation": activation,
        "weights_shape": [int(weights.shape[0]), int(weights.shape[1])],
        "weights": weights.tolist(),
        "biases_shape": [int(biases.shape[0])],
        "biases": biases.tolist(),
    }


def build_intermediate(model: SquashWorldModel) -> dict[str, Any]:
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "fully-connected",
            "precision": "float32",
            "framework": "pytorch",
            # Read current framebuffer + key(a0) one-hot.
            "input_mapping": "squash_fb_key_a0",
            "board_size": 20,
            "key_input_dim": 255,
            "keys": {"up": "j", "down": "k", "stay": " "},
        },
        "layers": [
            _layer_to_dict("layer_0", model.fc1, "relu"),
            _layer_to_dict("layer_1", model.fc2, "relu"),
            _layer_to_dict("layer_2", model.fc3, "none"),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export squash model to emulator JSON format")
    parser.add_argument("--checkpoint", default="squash_model.pth", help="Input checkpoint path")
    parser.add_argument(
        "--output",
        default="game-movement_generator.json",
        help="Output JSON path for emulator model compiler",
    )
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    out_path = Path(args.output)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    payload = torch.load(ckpt_path, map_location="cpu")
    state_dict = payload["model_state_dict"] if isinstance(payload, dict) and "model_state_dict" in payload else payload

    model = SquashWorldModel()
    model.load_state_dict(state_dict)
    model.eval()

    intermediate = build_intermediate(model)
    out_path.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
