#!/usr/bin/env python3
"""
Export deterministic modulo-255 counter network with 3 layers to match chargen depth.

This creates a counter with the same layer depth as the character generator:
- Layer 0: 255 -> 256 (shift embedded in first layer)
- Layer 1: 256 -> 256 (identity)
- Layer 2: 256 -> 255 (identity + final shift)

The overall behavior is still: output = (input + 1) mod 255
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

COUNTER255_MODULUS = 255


def build_counter255_three_layer() -> dict:
    """
    Build a 3-layer counter network.
    
    Layer 0: 255 -> 256
      - Maps input one-hot to a 256-dim space where position i maps to (i+1) mod 255
      - We'll use a weight matrix that shifts and pads
    
    Layer 1: 256 -> 256 (identity)
      - Pass-through layer
    
    Layer 2: 256 -> 255
      - Projects back to 255-dim with the shift applied
    """
    
    # Layer 0: 255 -> 256
    # We need to map one-hot at position i to a vector where argmax gives (i+1) mod 255
    # Simple approach: make weights such that input[i] contributes to output[(i+1) mod 255]
    # But output is 256-dim, so we need to handle the modulus
    
    layer0_weights = np.zeros((255, 256), dtype=np.float32)
    layer0_biases = np.zeros((256,), dtype=np.float32)
    
    for i in range(255):
        # Input i (one-hot) should produce output at position (i+1) mod 255
        out_pos = (i + 1) % 255
        layer0_weights[i, out_pos] = 1.0
    # Position 255 in output is unused (zero)
    
    # Layer 1: 256 -> 256 (identity)
    layer1_weights = np.eye(256, dtype=np.float32)
    layer1_biases = np.zeros((256,), dtype=np.float32)
    
    # Layer 2: 256 -> 255
    # Just take the first 255 dimensions (identity)
    layer2_weights = np.zeros((256, 255), dtype=np.float32)
    for i in range(255):
        layer2_weights[i, i] = 1.0
    # Input 255 maps nowhere (zero)
    layer2_biases = np.zeros((255,), dtype=np.float32)
    
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "counter255-three-layer",
            "precision": "float32",
            "framework": "oracle",
            "input_mapping": "counter255_a0_feedback",
            "counter_modulus": COUNTER255_MODULUS,
            "description": "3-layer deterministic modulo-255 counter network matching chargen depth",
        },
        "layers": [
            {
                "name": "counter255_layer0",
                "input_size": 255,
                "output_size": 256,
                "activation": "none",
                "weights_shape": [255, 256],
                "weights": layer0_weights.tolist(),
                "biases_shape": [256],
                "biases": layer0_biases.tolist(),
            },
            {
                "name": "counter255_layer1",
                "input_size": 256,
                "output_size": 256,
                "activation": "none",
                "weights_shape": [256, 256],
                "weights": layer1_weights.tolist(),
                "biases_shape": [256],
                "biases": layer1_biases.tolist(),
            },
            {
                "name": "counter255_layer2",
                "input_size": 256,
                "output_size": 255,
                "activation": "none",
                "weights_shape": [256, 255],
                "weights": layer2_weights.tolist(),
                "biases_shape": [255],
                "biases": layer2_biases.tolist(),
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export 3-layer modulo-255 counter model to emulator JSON"
    )
    parser.add_argument("--output", default="counter255_three_layer.json",
                        help="Output JSON path")
    args = parser.parse_args()

    payload = build_counter255_three_layer()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
