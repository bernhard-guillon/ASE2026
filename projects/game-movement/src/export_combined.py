#!/usr/bin/env python3
"""
Export Combined Model to Emulator JSON Format.

Exports the trained combined_model.pth to the emulator's intermediate JSON format.
This allows the model to be compiled and run as an ELF by the emulator.

Usage:
    python export_combined.py [--checkpoint PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

from combined_model import CombinedModel


def _layer_to_dict(name: str, layer: torch.nn.Linear, activation: str) -> dict[str, Any]:
    """Convert a linear layer to the emulator's JSON format."""
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


def build_combined_intermediate(model: CombinedModel) -> dict[str, Any]:
    """
    Build the intermediate JSON representation for the combined model.
    
    This matches the format expected by the emulator's model compiler.
    """
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "fully-connected",
            "precision": "float32",
            "framework": "pytorch",
            # Framebuffer input: 400 cells
            # No key input for autonomous mode
            "input_mapping": "framebuffer_400",
            "board_size": 20,
            "description": "Combined dual-model: physics + counter (Option 4a)",
        },
        "layers": [
            _layer_to_dict("combined_fc1", model.fc1, "relu"),
            _layer_to_dict("combined_fc2", model.fc2, "relu"),
            _layer_to_dict("combined_fc3", model.fc3, "relu"),
            _layer_to_dict("combined_fc4", model.fc4, "none"),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export combined model to emulator JSON")
    parser.add_argument("--checkpoint", default="combined_model.pth", help="Input checkpoint path")
    parser.add_argument("--output", default="game-movement-combined.json", help="Output JSON path")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    output_path = Path(args.output)

    if not checkpoint_path.exists():
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        return 1

    payload = torch.load(checkpoint_path, map_location="cpu")
    state_dict = payload["model_state_dict"] if isinstance(payload, dict) and "model_state_dict" in payload else payload

    model = CombinedModel()
    model.load_state_dict(state_dict)
    model.eval()

    intermediate = build_combined_intermediate(model)
    output_path.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
