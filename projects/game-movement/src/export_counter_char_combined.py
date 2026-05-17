#!/usr/bin/env python3
"""
Compose counter255 + chargen into a single staged model for emulator.

Output is a counter-char-staged architecture model ready for compiler.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export combined counter-chargen model")
    parser.add_argument("--counter-json", required=True, help="Counter255 model JSON")
    parser.add_argument("--chargen-json", required=True, help="Character generator JSON")
    parser.add_argument("--output", required=True, help="Output combined JSON")
    args = parser.parse_args()

    counter_path = Path(args.counter_json)
    chargen_path = Path(args.chargen_json)
    output_path = Path(args.output)

    if not counter_path.exists():
        print(f"ERROR: Counter JSON not found: {counter_path}")
        return 1
    if not chargen_path.exists():
        print(f"ERROR: Chargen JSON not found: {chargen_path}")
        return 1

    counter_data = json.loads(counter_path.read_text(encoding="utf-8"))
    chargen_data = json.loads(chargen_path.read_text(encoding="utf-8"))

    # Compose: counter layer + chargen layers
    combined = {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "counter-char-staged",
            "precision": "float32",
            "framework": "composed",
            "input_mapping": "counter_char_a0_bridge",
            "description": "Staged composition: counter255 layer 0 -> chargen layers 1..N",
            "counter_modulus": 255,
            "chargen_layers": len(chargen_data.get("layers", [])),
        },
        "layers": []
    }

    # Layer 0: counter
    if counter_data.get("layers"):
        combined["layers"].append(counter_data["layers"][0])

    # Layers 1+: chargen
    for i, layer in enumerate(chargen_data.get("layers", [])):
        layer_copy = layer.copy()
        # Rename to avoid collisions
        layer_copy["name"] = f"chargen_{i}"
        combined["layers"].append(layer_copy)

    output_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"Wrote combined model to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
