#!/usr/bin/env python3
"""
Export deterministic modulo-255 counter network to emulator JSON format.

Network:
- single dense layer: 255 -> 255
- no activation
- permutation weights implementing one-step shift:
    output[j] = input[(j - 1) mod 255]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from counter255_oracle import COUNTER255_MODULUS


def build_counter255_weights() -> tuple[np.ndarray, np.ndarray]:
    """
    Build counter255 weights that count starting from ASCII 'a' (97) and up.
    
    Maps: counter_tick_n -> chargen_input = (n + 97) % 255
    
    The permutation matrix maps:
        output[j] = input[(j - 1 - 97) mod 255]
        which computes: new_counter = (old_counter + 1) mod 255
        and: chargen_input = (counter + 97) mod 255
    """
    weights = np.zeros((COUNTER255_MODULUS, COUNTER255_MODULUS), dtype=np.float32)
    biases = np.zeros((COUNTER255_MODULUS,), dtype=np.float32)
    
    # Offset: ASCII 'a' = 97
    OFFSET = 97
    
    for out_idx in range(COUNTER255_MODULUS):
        # out_idx represents the next counter state
        # We want: output_idx = (input_idx + 1 + OFFSET) % 255
        # So input_idx = (output_idx - 1 - OFFSET) % 255
        in_idx = (out_idx - 1 - OFFSET) % COUNTER255_MODULUS
        weights[in_idx, out_idx] = 1.0
    
    return weights, biases


def build_counter255_intermediate() -> dict:
    weights, biases = build_counter255_weights()
    return {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "counter255-dense",
            "precision": "float32",
            "framework": "oracle",
            "input_mapping": "counter255_a0_feedback",
            "counter_modulus": COUNTER255_MODULUS,
        "description": "Deterministic modulo-255 counter network: outputs chargen_index = (counter + 97) mod 255, starting at ASCII 'a'",
        },
        "layers": [
            {
                "name": "counter255_shift",
                "input_size": COUNTER255_MODULUS,
                "output_size": COUNTER255_MODULUS,
                "activation": "none",
                "weights_shape": [COUNTER255_MODULUS, COUNTER255_MODULUS],
                "weights": weights.tolist(),
                "biases_shape": [COUNTER255_MODULUS],
                "biases": biases.tolist(),
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export modulo-255 counter model to emulator JSON")
    parser.add_argument("--output", default="counter255_generator.json", help="Output JSON path")
    args = parser.parse_args()

    payload = build_counter255_intermediate()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

