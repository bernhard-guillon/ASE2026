#!/usr/bin/env python3
"""
Export a static counter-to-character model.

Unlike counter255_a0_feedback, this version:
- Takes a one-hot 255 input (the character index to display)
- Passes it through to chargen to generate the pixel representation
- Does NOT auto-increment the counter state
- Effectively "freezes" the character display

This allows us to test: counter_input=0 -> chargen_input=97 (character 'a')
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def build_counter_char_static_weights() -> tuple[np.ndarray, np.ndarray]:
    """
    Build a pass-through layer that just applies ASCII offset.
    
    Input: one-hot 255 (counter position 0..254)
    Output: one-hot 255 (chargen input 97..254+97 mod 255)
    
    This is a simple permutation matrix.
    """
    weights = np.zeros((255, 255), dtype=np.float32)
    biases = np.zeros(255, dtype=np.float32)
    
    OFFSET = 97
    for in_idx in range(255):
        out_idx = (in_idx + OFFSET) % 255
        weights[in_idx, out_idx] = 1.0
    
    return weights, biases


def build_counter_char_static_model() -> dict:
    """Build a static counter-to-chargen-input mapping model."""
    weights, biases = build_counter_char_static_weights()
    
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "counter-char-static",
            "precision": "float32",
            "framework": "oracle",
            "input_mapping": "counter_char_a0_bridge",
            "description": "Static counter->chargen bridge: displays character for current counter value (no auto-increment)",
        },
        "layers": [
            {
                "name": "counter_to_chargen_offset",
                "input_size": 255,
                "output_size": 255,
                "activation": "none",
                "weights_shape": [255, 255],
                "weights": weights.tolist(),
                "biases_shape": [255],
                "biases": biases.tolist(),
            }
        ],
    }


def main() -> int:
    import argparse
    
    parser = argparse.ArgumentParser(description="Export static counter-chargen bridge model")
    parser.add_argument("--output", default="counter_char_static.json", help="Output JSON path")
    args = parser.parse_args()

    model = build_counter_char_static_model()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
