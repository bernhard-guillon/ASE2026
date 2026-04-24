"""
Unit tests for deterministic movement oracle and dataset generation.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from movement_dataset import ACTIONS, BOARD_SIZE, generate_movement_dataset, transition_oracle


class MovementOracleTests(unittest.TestCase):
    def test_corner_clamp_top_left(self):
        self.assertEqual(transition_oracle(0, 0, "up"), (0, 0))
        self.assertEqual(transition_oracle(0, 0, "left"), (0, 0))
        self.assertEqual(transition_oracle(0, 0, "down"), (0, 1))
        self.assertEqual(transition_oracle(0, 0, "right"), (1, 0))

    def test_corner_clamp_bottom_right(self):
        mx = BOARD_SIZE - 1
        self.assertEqual(transition_oracle(mx, mx, "down"), (mx, mx))
        self.assertEqual(transition_oracle(mx, mx, "right"), (mx, mx))
        self.assertEqual(transition_oracle(mx, mx, "up"), (mx, mx - 1))
        self.assertEqual(transition_oracle(mx, mx, "left"), (mx - 1, mx))

    def test_center_moves(self):
        self.assertEqual(transition_oracle(10, 10, "up"), (10, 9))
        self.assertEqual(transition_oracle(10, 10, "down"), (10, 11))
        self.assertEqual(transition_oracle(10, 10, "left"), (9, 10))
        self.assertEqual(transition_oracle(10, 10, "right"), (11, 10))
        self.assertEqual(transition_oracle(10, 10, "stay"), (10, 10))

    def test_exhaustive_in_bounds(self):
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                for action in ACTIONS:
                    nx, ny = transition_oracle(x, y, action)
                    self.assertGreaterEqual(nx, 0)
                    self.assertGreaterEqual(ny, 0)
                    self.assertLess(nx, BOARD_SIZE)
                    self.assertLess(ny, BOARD_SIZE)

    def test_dataset_shape_and_count(self):
        with TemporaryDirectory() as td:
            arrays = generate_movement_dataset(
                npz_path=Path(td) / "movement_dataset_test_tmp.npz",
                json_path=Path(td) / "movement_transitions_test_tmp.json",
            )
            self.assertEqual(arrays["x"].shape, (BOARD_SIZE * BOARD_SIZE * len(ACTIONS), 405))
            self.assertEqual(arrays["y"].shape, (BOARD_SIZE * BOARD_SIZE * len(ACTIONS), 400))


if __name__ == "__main__":
    unittest.main()
