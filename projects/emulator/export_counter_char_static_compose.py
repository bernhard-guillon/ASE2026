#!/usr/bin/env python3
"""
Compose static counter-chargen model for testing.

Instead of auto-incrementing, this version:
1. Takes external counter input (via a0 register)
2. Maps to chargen input range (add 97 offset)
3. Generates character display
4. Does NOT auto-increment on next cycle

Perfect for testing: set counter=0 at boot, should display 'a' forever.
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


def compose_models(offset_json: dict, chargen_json: dict) -> dict:
    """
    Compose static offset layer + chargen layers.
    
    The forward pass:
    1. Load external counter from a0 as one-hot into input buffer
    2. Run offset layer: counter_idx -> chargen_idx (add 97)
    3. Run chargen layers on chargen_idx input
    4. Output 400 pixel frame (no feedback to a0)
    """

    # Extract layers
    offset_layers = offset_json.get("layers", [])
    chargen_layers = chargen_json.get("layers", [])
    
    if not offset_layers:
        raise ValueError("Offset model has no layers")
    if not chargen_layers:
        raise ValueError("Chargen model has no layers")

    combined_layers = offset_layers + chargen_layers

    # Get metadata
    offset_meta = offset_json.get("metadata", {})
    chargen_meta = chargen_json.get("metadata", {})

    # Output size is chargen's final layer
    final_output_size = chargen_layers[-1].get("output_size", 400)

    combined = {
        "metadata": {
            "description": "Static counter-chargen: displays character without auto-increment",
            "model_type": "generator",
            "version": 1,
            "architecture": "counter-char-static",
            "precision": offset_meta.get("precision", chargen_meta.get("precision", "float32")),
            "framework": "hybrid",
            "counter_modulus": 255,
            "bridge_mechanism": "a0_register_noincrement",
            "stages": ["load_counter_from_a0", "offset_to_chargen_idx", "chargen_forward", "output_pixels"]
        },
        "input_mapping": "counter_char_a0_bridge",
        # Note: no output feedback to a0; just render pixels
        "layers": combined_layers,
        "input_size": offset_json.get("input_size", 1),
        "output_size": final_output_size,  # 400 for chargen's 20x20
    }

    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose static counter + chargen")
    parser.add_argument("--offset-json", required=True, help="Path to offset model JSON")
    parser.add_argument("--chargen-json", required=True, help="Path to chargen model JSON")
    parser.add_argument("--output", required=True, help="Path to output combined model JSON")

    args = parser.parse_args()

    try:
        offset = load_json(args.offset_json)
        chargen = load_json(args.chargen_json)
        combined = compose_models(offset, chargen)
        save_json(combined, args.output)
        print(f"Successfully composed static counter-chargen model: {args.output}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
