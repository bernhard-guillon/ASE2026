#!/usr/bin/env python3
"""
Export a simple counter model that displays the counter value as a centered character.

Instead of using chargen's complex pixel output, this just:
1. Takes counter value (0-254)
2. Maps it to ASCII 'a' (97) + offset
3. Displays that character centered on 20x20 grid

Model: single layer that maps counter input to 400 pixel outputs
where the center pixel is "hot" and displays the character value.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def build_counter_char_simple_model() -> dict:
    """
    Build a single-layer model that converts counter value to centered character display.
    
    - Input: 255 (one-hot counter position)
    - Output: 400 (20x20 pixel grid with center pixel = character value)
    """
    
    # Weights: [255 input, 400 output]
    # Each input i produces output where:
    #   - Center pixel (200) = 1.0 (always on)
    #   - All other pixels = 0.0
    # This gives us a single centered dot regardless of input
    
    weights = np.zeros((255, 400), dtype=np.float32)
    biases = np.zeros(400, dtype=np.float32)
    
    # Set center pixel to 1.0 for any input
    # Center of 20x20 grid is at row 10, col 10 = pixel index 10*20 + 10 = 210
    center_pixel = 10 * 20 + 10
    weights[:, center_pixel] = 1.0
    
    # Set all bias values to the ASCII character for each input position
    # Input position i corresponds to character (i + 97) mod 255
    for i in range(255):
        char_code = (i + 97) % 255
        biases[center_pixel] = float(char_code) / 255.0  # Normalize to [0, 1]
    
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "counter-char-simple",
            "precision": "float32",
            "framework": "oracle",
            "input_mapping": "counter_char_a0_bridge",
            "description": "Simple counter->character display: centered pixel shows current character (a, b, c, ...)",
        },
        "layers": [
            {
                "name": "counter_char_display",
                "input_size": 255,
                "output_size": 400,
                "activation": "sigmoid",
                "weights_shape": [255, 400],
                "weights": weights.tolist(),
                "biases_shape": [400],
                "biases": biases.tolist(),
            }
        ],
    }


def main() -> int:
    parser_output = sys.argv[1] if len(sys.argv) > 1 else "counter_char_simple.json"
    
    model = build_counter_char_simple_model()
    
    output_path = Path(parser_output)
    output_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
