#!/usr/bin/env python3
"""
Unit tests for staged counter->char forward pass code generation.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from model_compiler import ModelCompiler


class CounterCharForwardCodegenTests(unittest.TestCase):
    def test_staged_forward_pass_codegen_present(self) -> None:
        model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "counter-char-staged",
                "precision": "float32",
                "framework": "oracle",
                "input_mapping": "counter_char_a0_bridge",
            },
            "layers": [
                {
                    "name": "counter",
                    "input_size": 255,
                    "output_size": 255,
                    "activation": "none",
                    "weights_shape": [255, 255],
                    "weights": [[0.0] * 255 for _ in range(255)],
                    "biases_shape": [255],
                    "biases": [0.0] * 255,
                },
                {
                    "name": "char_out",
                    "input_size": 255,
                    "output_size": 400,
                    "activation": "none",
                    "weights_shape": [255, 400],
                    "weights": [[0.0] * 400 for _ in range(255)],
                    "biases_shape": [400],
                    "biases": [0.0] * 400,
                },
            ],
        }

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            json_path = td_path / "model.json"
            asm_path = td_path / "model.s"
            bin_path = td_path / "model.bin"
            json_path.write_text(json.dumps(model), encoding="utf-8")

            compiler = ModelCompiler(verbose=False)
            compiler.generate_assembly(
                str(json_path),
                str(asm_path),
                str(bin_path),
                with_bootloader=False,
                with_execution=True,
            )

            asm = asm_path.read_text(encoding="utf-8")
            self.assertIn("# Forward pass (counter-char staged)", asm)
            self.assertIn("call layer_0_forward", asm)
            self.assertIn("call layer_1_forward", asm)
            self.assertIn("counter_char", asm)


if __name__ == "__main__":
    unittest.main()

