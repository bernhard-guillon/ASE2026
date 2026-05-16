"""
Unit tests for squash oracle and dataset generation.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from squash_dataset import (
    BOARD_SIZE,
    KEY_DIM,
    KEY_TO_ACTION,
    SquashState,
    generate_squash_dataset,
    key_to_onehot,
    step_oracle,
)


class SquashOracleTests(unittest.TestCase):
    def test_key_onehot_shape(self):
        vec = key_to_onehot("j")
        self.assertEqual(vec.shape, (KEY_DIM,))
        self.assertEqual(float(vec.sum()), 1.0)
        self.assertEqual(vec[ord("j")], 1.0)

    def test_paddle_clamp(self):
        state = SquashState(ball_x=5, ball_y=5, ball_dx=1, ball_dy=0, paddle_top=0, game_over=False)
        nxt = step_oracle(state, KEY_TO_ACTION["j"])
        self.assertEqual(nxt.paddle_top, 0)

        state = SquashState(
            ball_x=5,
            ball_y=5,
            ball_dx=1,
            ball_dy=0,
            paddle_top=BOARD_SIZE - 3,
            game_over=False,
        )
        nxt = step_oracle(state, KEY_TO_ACTION["k"])
        self.assertEqual(nxt.paddle_top, BOARD_SIZE - 3)

    def test_wall_reflection(self):
        # top bounce
        state = SquashState(ball_x=10, ball_y=0, ball_dx=1, ball_dy=-1, paddle_top=9, game_over=False)
        nxt = step_oracle(state, 0)
        self.assertEqual(nxt.ball_dy, 1)

        # left bounce
        state = SquashState(ball_x=0, ball_y=10, ball_dx=-1, ball_dy=0, paddle_top=9, game_over=False)
        nxt = step_oracle(state, 0)
        self.assertEqual(nxt.ball_dx, 1)

    def test_right_side_miss_game_over(self):
        state = SquashState(ball_x=18, ball_y=10, ball_dx=1, ball_dy=0, paddle_top=0, game_over=False)
        nxt = step_oracle(state, 0)
        self.assertTrue(nxt.game_over)

    def test_dataset_shapes(self):
        with TemporaryDirectory() as td:
            arrays = generate_squash_dataset(
                npz_path=Path(td) / "squash_dataset_test_tmp.npz",
                json_path=Path(td) / "squash_transitions_test_tmp.json",
                episodes=16,
                steps_per_episode=20,
                seed=7,
            )
            self.assertGreater(arrays["x"].shape[0], 0)
            self.assertEqual(arrays["x"].shape[1], 400 + 255)
            self.assertEqual(arrays["y"].shape[1], 400)


if __name__ == "__main__":
    unittest.main()
