#!/usr/bin/env python3
"""
Compose counter255 model with character generator model.

Expects two model JSONs:
- counter255_json: single layer counter model (output: 255)
- chargen_json: multi-layer character generator (input: 255, output: 256 one-hot)

Outputs a single combined model using "counter-char-staged" architecture:
- Layers are concatenated
- Input mapping: counter_char_a0_bridge (single scalar into one-hot)
- Output mapping: unchanged from chargen
- Architecture: counter-char-staged (triggers staged forward pass in compiler)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_json(data: dict, path: str) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def compose_models(counter_json: dict, chargen_json: dict) -> dict:
    """
    Compose counter255 + chargen into one staged model.

    The staged forward pass works as:
    1. Layer 0 (counter): produces 255-element output
    2. Argmax layer 0 output -> write to a0 register
    3. Rebuild one-hot from a0 value (via a0_bridge input mapping)
    4. Feed one-hot as input to layers 1..N (chargen)
    """

    # Extract counter model layer
    counter_layers = counter_json.get("layers", [])
    if not counter_layers:
        raise ValueError("Counter model has no layers")

    counter_layer = counter_layers[0]

    # Extract chargen model layers
    chargen_layers = chargen_json.get("layers", [])
    if not chargen_layers:
        raise ValueError("Chargen model has no layers")

    # Compose: counter_layer + chargen_layers
    combined_layers = [counter_layer] + chargen_layers

    # Get metadata from both sources
    counter_meta = counter_json.get("metadata", {})
    chargen_meta = chargen_json.get("metadata", {})

    # Build combined model
    combined = {
        "metadata": {
            "description": "Combined counter-chargen model (staged)",
            "model_type": "generator",
            "version": 1,
            "architecture": "counter-char-staged",
            "precision": counter_meta.get("precision", chargen_meta.get("precision", "float32")),
            "framework": "hybrid",
            "counter_modulus": 255,
            "bridge_mechanism": "a0_register",
            "stages": ["counter_output", "a0_write", "a0_rebuild_to_onehot", "chargen_forward"]
        },
        "input_mapping": "counter_char_a0_bridge",
        "output_mapping": chargen_json.get("output_mapping", "framebuffer_argmax_u8"),
        "layers": combined_layers,
        "input_size": counter_json.get("input_size", 1),  # Counter takes no real input (scalar constant)
        "output_size": chargen_json.get("output_size", 256),
    }

    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose counter255 + chargen models")
    parser.add_argument("--counter-json", required=True, help="Path to counter255 model JSON")
    parser.add_argument("--chargen-json", required=True, help="Path to chargen model JSON")
    parser.add_argument("--output", required=True, help="Path to output combined model JSON")

    args = parser.parse_args()

    try:
        counter = load_json(args.counter_json)
        chargen = load_json(args.chargen_json)
        combined = compose_models(counter, chargen)
        save_json(combined, args.output)
        print(f"Successfully composed combined model: {args.output}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
