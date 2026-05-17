"""
Tests for modulo-255 counter oracle and deterministic export shape.
"""

from __future__ import annotations

import unittest

import numpy as np

from counter255_oracle import COUNTER255_MODULUS, counter255_step
from generate_counter255_dataset import generate_counter255_dataset
from export_counter255_intermediate import build_counter255_intermediate


class Counter255OracleTests(unittest.TestCase):
    def test_step_increments(self) -> None:
        self.assertEqual(counter255_step(0), 1)
        self.assertEqual(counter255_step(42), 43)

    def test_wraps_at_254(self) -> None:
        self.assertEqual(counter255_step(254), 0)

    def test_invalid_state_raises(self) -> None:
        with self.assertRaises(ValueError):
            counter255_step(-1)
        with self.assertRaises(ValueError):
            counter255_step(255)


class Counter255DatasetTests(unittest.TestCase):
    def test_dataset_shapes_and_mapping(self) -> None:
        arrays = generate_counter255_dataset("/tmp/counter255_dataset.npz", "/tmp/counter255_transitions.json")
        x = arrays["x"]
        y = arrays["y"]
        self.assertEqual(x.shape, (255, 255))
        self.assertEqual(y.shape, (255, 255))
        # one-hot rows
        self.assertTrue(np.allclose(x.sum(axis=1), 1.0))
        self.assertTrue(np.allclose(y.sum(axis=1), 1.0))
        # transition semantics
        for n in (0, 1, 42, 254):
            self.assertEqual(int(np.argmax(y[n])), (n + 1) % 255)


class Counter255ExportTests(unittest.TestCase):
    def test_export_payload_shape(self) -> None:
        payload = build_counter255_intermediate()
        self.assertEqual(payload["metadata"]["counter_modulus"], COUNTER255_MODULUS)
        self.assertEqual(payload["metadata"]["input_mapping"], "counter255_a0_feedback")
        self.assertEqual(len(payload["layers"]), 1)
        layer = payload["layers"][0]
        self.assertEqual(layer["input_size"], 255)
        self.assertEqual(layer["output_size"], 255)
        self.assertEqual(layer["activation"], "none")


if __name__ == "__main__":
    unittest.main()

