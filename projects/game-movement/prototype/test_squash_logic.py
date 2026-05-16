#!/usr/bin/env python3
"""
Minimal rule checks for terminal_squash prototype logic.
"""

from terminal_squash import SquashGame


def test_paddle_clamp() -> None:
    game = SquashGame(seed=1)
    game.paddle_top = 0
    game.move_paddle(-1)
    assert game.paddle_top == 0

    game.paddle_top = game.height - game.paddle_height
    game.move_paddle(1)
    assert game.paddle_top == game.height - game.paddle_height


def test_top_bottom_reflection() -> None:
    game = SquashGame(seed=1)
    game.ball_x, game.ball_y = 5, 0
    game.ball_dx, game.ball_dy = 1, -1
    game.step(0)
    assert game.ball_dy == 1

    game.ball_x, game.ball_y = 5, game.height - 1
    game.ball_dx, game.ball_dy = 1, 1
    game.step(0)
    assert game.ball_dy == -1


def test_left_wall_reflection() -> None:
    game = SquashGame(seed=1)
    game.ball_x, game.ball_y = 0, 10
    game.ball_dx, game.ball_dy = -1, 0
    game.step(0)
    assert game.ball_dx == 1
    assert game.ball_x == 1


def test_paddle_hit_bounce() -> None:
    game = SquashGame(seed=1)
    game.paddle_top = 9
    game.ball_x, game.ball_y = 18, 10
    game.ball_dx, game.ball_dy = 1, 0
    game.step(0)
    assert not game.game_over
    assert game.ball_dx == -1
    assert game.ball_x == 17


def test_right_side_miss_is_loss() -> None:
    game = SquashGame(seed=1)
    game.paddle_top = 0
    game.ball_x, game.ball_y = 18, 10
    game.ball_dx, game.ball_dy = 1, 0
    game.step(0)
    assert game.game_over


def main() -> int:
    test_paddle_clamp()
    test_top_bottom_reflection()
    test_left_wall_reflection()
    test_paddle_hit_bounce()
    test_right_side_miss_is_loss()
    print("Prototype squash logic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
