#!/usr/bin/env python3
"""
Export scripts for dual-model system (Physics + Counter).

This script exports trained PyTorch models to the emulator's JSON intermediate format.
Each model is exported separately and can be combined or used independently.

Usage:
    python export_dual_model.py physics [--checkpoint PATH] [--output PATH]
    python export_dual_model.py counter [--checkpoint PATH] [--output PATH]
    python export_dual_model.py both [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

from physics_model import PhysicsNetwork, PHYSICS_INPUT_SIZE, PHYSICS_OUTPUT_SIZE
from counter_model import CounterNetwork, COUNTER_INPUT_SIZE, COUNTER_OUTPUT_SIZE
from dual_model_contract import GRID_SIZE


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


def export_physics_model(
    checkpoint_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """
    Export physics model to emulator JSON format.
    
    Model structure:
    - Input: 47 (ball_x one-hot 20 + ball_y one-hot 20 + vel_x one-hot 3 + vel_y one-hot 3 + stop 1)
    - Hidden: 128, ReLU
    - Hidden: 128, ReLU  
    - Output: 47 (same structure as input, representing next state + hit_wall)
    """
    checkpoint_path = Path(checkpoint_path)
    output_path = Path(output_path)
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Physics checkpoint not found: {checkpoint_path}")
    
    payload = torch.load(checkpoint_path, map_location="cpu")
    state_dict = payload["model_state_dict"] if isinstance(payload, dict) and "model_state_dict" in payload else payload
    
    model = PhysicsNetwork()
    model.load_state_dict(state_dict)
    model.eval()
    
    intermediate = {
        "metadata": {
            "model_type": "physics",
            "version": 1,
            "architecture": "fully-connected",
            "precision": "float32",
            "framework": "pytorch",
            "grid_size": GRID_SIZE,
            "input_size": PHYSICS_INPUT_SIZE,
            "output_size": PHYSICS_OUTPUT_SIZE,
            "description": "Model A: Physics - predicts next ball position, velocity, and hit_wall",
        },
        "layers": [
            _layer_to_dict("physics_fc1", model.fc1, "relu"),
            _layer_to_dict("physics_fc2", model.fc2, "relu"),
            _layer_to_dict("physics_fc3", model.fc3, "none"),
        ],
    }
    
    output_path.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")
    print(f"Wrote physics model to {output_path} ({output_path.stat().st_size} bytes)")
    return intermediate


def export_counter_model(
    checkpoint_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """
    Export counter model to emulator JSON format.
    
    Model structure:
    - Input: 12 (count one-hot 10 + stop 1 + hit_wall 1)
    - Hidden: 64, ReLU
    - Hidden: 64, ReLU
    - Output: 11 (count one-hot 10 + stop 1)
    """
    checkpoint_path = Path(checkpoint_path)
    output_path = Path(output_path)
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Counter checkpoint not found: {checkpoint_path}")
    
    payload = torch.load(checkpoint_path, map_location="cpu")
    state_dict = payload["model_state_dict"] if isinstance(payload, dict) and "model_state_dict" in payload else payload
    
    model = CounterNetwork()
    model.load_state_dict(state_dict)
    model.eval()
    
    intermediate = {
        "metadata": {
            "model_type": "counter",
            "version": 1,
            "architecture": "fully-connected",
            "precision": "float32",
            "framework": "pytorch",
            "input_size": COUNTER_INPUT_SIZE,
            "output_size": COUNTER_OUTPUT_SIZE,
            "description": "Model B: Counter - predicts next count and stop bit",
        },
        "layers": [
            _layer_to_dict("counter_fc1", model.fc1, "relu"),
            _layer_to_dict("counter_fc2", model.fc2, "relu"),
            _layer_to_dict("counter_fc3", model.fc3, "none"),
        ],
    }
    
    output_path.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")
    print(f"Wrote counter model to {output_path} ({output_path.stat().st_size} bytes)")
    return intermediate


def export_both_models(
    physics_checkpoint: str | Path = "physics_model.pth",
    counter_checkpoint: str | Path = "counter_model.pth",
    output_dir: str | Path = ".",
) -> tuple[dict, dict]:
    """Export both physics and counter models."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    physics_output = output_dir / "physics_model.json"
    counter_output = output_dir / "counter_model.json"
    
    physics_ir = export_physics_model(physics_checkpoint, physics_output)
    counter_ir = export_counter_model(counter_checkpoint, counter_output)
    
    return physics_ir, counter_ir


def main() -> int:
    parser = argparse.ArgumentParser(description="Export dual-model system to emulator JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Physics subcommand
    physics_parser = subparsers.add_parser("physics", help="Export physics model")
    physics_parser.add_argument("--checkpoint", default="physics_model.pth", help="Physics checkpoint path")
    physics_parser.add_argument("--output", default="physics_model.json", help="Output JSON path")
    
    # Counter subcommand
    counter_parser = subparsers.add_parser("counter", help="Export counter model")
    counter_parser.add_argument("--checkpoint", default="counter_model.pth", help="Counter checkpoint path")
    counter_parser.add_argument("--output", default="counter_model.json", help="Output JSON path")
    
    # Both subcommand
    both_parser = subparsers.add_parser("both", help="Export both models")
    both_parser.add_argument("--physics-checkpoint", default="physics_model.pth", help="Physics checkpoint path")
    both_parser.add_argument("--counter-checkpoint", default="counter_model.pth", help="Counter checkpoint path")
    both_parser.add_argument("--output-dir", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "physics":
        export_physics_model(args.checkpoint, args.output)
    elif args.command == "counter":
        export_counter_model(args.checkpoint, args.output)
    elif args.command == "both":
        export_both_models(args.physics_checkpoint, args.counter_checkpoint, args.output_dir)
    else:
        print(f"Unknown command: {args.command}")
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
