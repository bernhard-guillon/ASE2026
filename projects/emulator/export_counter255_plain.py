#!/usr/bin/env python3
"""
Export deterministic modulo-255 counter network to emulator JSON format.

This variant increments the current a0 value by one without applying the
ASCII offset used by the standalone static counter-char demo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

COUNTER255_MODULUS = 255


def build_counter255_weights() -> tuple[np.ndarray, np.ndarray]:
    """
    Build counter weights that implement:
        output_idx = (input_idx + 1) mod 255
    """
    weights = np.zeros((COUNTER255_MODULUS, COUNTER255_MODULUS), dtype=np.float32)
    biases = np.zeros((COUNTER255_MODULUS,), dtype=np.float32)

    for out_idx in range(COUNTER255_MODULUS):
        in_idx = (out_idx - 1) % COUNTER255_MODULUS
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
            "description": "Deterministic modulo-255 counter network: outputs chargen_index = (counter + 1) mod 255",
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
