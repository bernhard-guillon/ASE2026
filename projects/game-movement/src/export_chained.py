#!/usr/bin/env python3
"""
Export Chained Model to Emulator JSON Format.

Exports the chained model (containing both physics and counter sub-networks)
to the emulator's intermediate JSON format. This allows the model to be
compiled and run as an ELF by the emulator.

The chained model has:
- Physics sub-network layers (frozen)
- Counter sub-network layers (frozen)
- No connections between the two sub-networks except through control bits

Usage:
    python export_chained.py [--physics-checkpoint PATH] [--counter-checkpoint PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

from chained_model import ChainedModel, CHAINED_INPUT_SIZE, CHAINED_OUTPUT_SIZE


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


def build_chained_intermediate(model: ChainedModel) -> dict[str, Any]:
    """
    Build the intermediate JSON representation for the chained model.
    
    The chained model contains:
    - Physics sub-network: 3 layers (47->128->128->47)
    - Counter sub-network: 3 layers (12->64->64->11)
    - Total: 6 layers with no cross-connections
    """
    layers = []
    
    # Physics sub-network layers
    layers.append(_layer_to_dict("chained_physics_fc1", model.physics.fc1, "relu"))
    layers.append(_layer_to_dict("chained_physics_fc2", model.physics.fc2, "relu"))
    layers.append(_layer_to_dict("chained_physics_fc3", model.physics.fc3, "none"))
    
    # Counter sub-network layers
    layers.append(_layer_to_dict("chained_counter_fc1", model.counter.fc1, "relu"))
    layers.append(_layer_to_dict("chained_counter_fc2", model.counter.fc2, "relu"))
    layers.append(_layer_to_dict("chained_counter_fc3", model.counter.fc3, "none"))
    
    return {
        "metadata": {
            "model_type": "chained",
            "version": 1,
            "architecture": "dual-model-chained",
            "precision": "float32",
            "framework": "pytorch",
            "input_size": CHAINED_INPUT_SIZE,
            "output_size": CHAINED_OUTPUT_SIZE,
            "description": "Chained model: physics + counter sub-networks with control bit wiring (Option 4a)",
            "sub_networks": {
                "physics": {
                    "input_size": 47,
                    "output_size": 47,
                    "layers": ["chained_physics_fc1", "chained_physics_fc2", "chained_physics_fc3"],
                },
                "counter": {
                    "input_size": 12,
                    "output_size": 11,
                    "layers": ["chained_counter_fc1", "chained_counter_fc2", "chained_counter_fc3"],
                },
            },
            "wiring": {
                "physics_input": "input[0:46] + input[56] (stop bit)",
                "physics_output": "output[0:46] (next physics state) + output[46] (hit_wall)",
                "counter_input": "input[46:57] (counter state) + physics_output[46] (hit_wall)",
                "counter_output": "output[46:57] (next counter state)",
            },
        },
        "layers": layers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export chained model to emulator JSON")
    parser.add_argument("--physics-checkpoint", default=None, help="Physics model checkpoint path")
    parser.add_argument("--counter-checkpoint", default=None, help="Counter model checkpoint path")
    parser.add_argument("--output", default="chained_model.json", help="Output JSON path")
    args = parser.parse_args()

    output_path = Path(args.output)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    model = ChainedModel()
    
    # Load pre-trained weights if provided
    if args.physics_checkpoint or args.counter_checkpoint:
        from chained_model import create_chained_model
        model = create_chained_model(
            physics_checkpoint=args.physics_checkpoint,
            counter_checkpoint=args.counter_checkpoint,
            device=device,
        )
    
    intermediate = build_chained_intermediate(model)
    output_path.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")
    print(f"Wrote chained model to {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
