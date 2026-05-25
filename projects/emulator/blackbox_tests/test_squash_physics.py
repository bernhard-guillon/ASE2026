"""
Test reference squash physics function.
Verifies the deterministic physics for all state combinations.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from squash_physics import (
    BALL_X_RANGE, BALL_Y_RANGE, BALL_V_RANGE, PADDLE_Y_RANGE,
    GAME_STATE_RANGE, KEY_RANGE, PADDLE_HEIGHT, INPUT_SIZE, OUTPUT_SIZE,
    squash_physics, encode_input, encode_output, decode_output, decode_state,
    generate_all_game_state_samples, one_hot, argmax,
)


def test_physics_left_wall_bounce():
    """Ball bounces off left wall when paddle overlap exists."""
    # Ball at x=0, y=5, moving left — bounces off left wall even without paddle
    bx, by, vx, vy, py, gs, ku, kd = 0, 5, 0, 0, 2, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert nvx == 1, f"Expected vx→1 (bounce right), got {nvx}"
    assert nbx == 0, f"Expected bx clamped to 0, got {nbx}"
    assert ngs == 0, "Game should still be live"


def test_physics_left_wall_no_paddle():
    """Ball exits left edge without paddle overlap → game over."""
    bx, by, vx, vy, py, gs, ku, kd = 0, 0, 0, 0, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    # Ball at y=0, paddle at y=5 → no overlap → game over
    assert nbx == 0, f"Expected bx=0 at left edge, got {nbx}"
    assert ngs == 1, f"Expected game_state=1 on paddle miss, got {ngs}"


def test_physics_top_wall():
    """Ball moving up hits top wall → bounces down."""
    bx, by, vx, vy, py, gs, ku, kd = 10, 0, 1, 0, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    # vy=0 means up, ball at y=0 → nby = -1
    # Top wall bounce: nby < 0 → nby=0, nvy=1 (down)
    assert nby == 0, f"Expected by=0 after top bounce, got {nby}"
    assert nvy == 1, f"Expected vy→1 (down) after top bounce, got {nvy}"


def test_physics_bottom_wall():
    """Ball moving down hits bottom wall → bounces up."""
    bx, by, vx, vy, py, gs, ku, kd = 10, 14, 1, 1, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    # vy=1 means down, ball at y=14 → nby = 15
    # Bottom wall bounce: nby >= 15 → nby=14, nvy=0 (up)
    assert nby == BALL_Y_RANGE - 1, f"Expected by=14 after bottom bounce, got {nby}"
    assert nvy == 0, f"Expected vy→0 (up) after bottom bounce, got {nvy}"


def test_physics_right_wall_bounce():
    """Ball exits right boundary → bounces left, game stays live."""
    bx, by, vx, vy, py, gs, ku, kd = 19, 7, 1, 0, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert nvx == 0, f"Expected vx→0 (bounce left), got {nvx}"
    assert nbx == BALL_X_RANGE - 1, f"Expected bx clamped to {BALL_X_RANGE-1}, got {nbx}"
    assert ngs == 0, "Game should still be live"


def test_physics_left_edge_paddle_miss():
    """Ball exits left edge without paddle overlap → game_state=1."""
    bx, by, vx, vy, py, gs, ku, kd = 0, 10, 0, 0, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    # Ball at y=10, paddle at y=5 → no overlap (ball rows [10,11], paddle rows [5,9])
    assert ngs == 1, f"Expected game_state=1 on paddle miss, got {ngs}"
    assert nbx == 0, f"Expected bx=0 at left edge, got {nbx}"


def test_physics_frozen_on_loss():
    """Once game_state=1, state does not change."""
    bx, by, vx, vy, py, gs, ku, kd = 5, 5, 1, 0, 5, 1, 1, 1
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert (nbx, nby, nvx, nvy, npy, ngs) == (bx, by, vx, vy, py, gs), \
        "State should be frozen when game_state=1"


def test_physics_paddle_move_up():
    """Pressing key_up moves paddle up."""
    bx, by, vx, vy, py, gs, ku, kd = 5, 5, 1, 0, 5, 0, 1, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert npy == 3, f"Expected paddle_y=3 after up, got {npy}"


def test_physics_paddle_move_down():
    """Pressing key_down moves paddle down."""
    bx, by, vx, vy, py, gs, ku, kd = 5, 5, 1, 0, 5, 0, 0, 1
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert npy == 7, f"Expected paddle_y=7 after down, got {npy}"


def test_physics_paddle_clamp_top():
    """Paddle clamped at top edge."""
    bx, by, vx, vy, py, gs, ku, kd = 5, 5, 1, 0, 0, 0, 1, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert npy == 0, f"Expected paddle_y=0 (clamped), got {npy}"


def test_physics_paddle_clamp_bottom():
    """Paddle clamped at bottom edge."""
    bx, by, vx, vy, py, gs, ku, kd = 5, 5, 1, 0, 10, 0, 0, 1
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert npy == 10, f"Expected paddle_y=10 (clamped), got {npy}"


def test_physics_encode_decode_roundtrip():
    """Encode→decode roundtrip is lossless for a subset of states."""
    import random
    rng = random.Random(42)
    for _ in range(5000):
        bx = rng.randint(0, BALL_X_RANGE - 1)
        by = rng.randint(0, BALL_Y_RANGE - 1)
        vx = rng.randint(0, BALL_V_RANGE - 1)
        vy = rng.randint(0, BALL_V_RANGE - 1)
        py = rng.randint(0, PADDLE_Y_RANGE - 1)
        gs = rng.randint(0, GAME_STATE_RANGE - 1)
        ku = rng.randint(0, KEY_RANGE - 1)
        kd = rng.randint(0, KEY_RANGE - 1)
        inp = encode_input(bx, by, vx, vy, py, gs, ku, kd)
        dbx, dby, dvx, dvy, dpy, dgs, dku, dkd = decode_state(inp)
        assert (bx, by, vx, vy, py, gs, ku, kd) == (dbx, dby, dvx, dvy, dpy, dgs, dku, dkd), \
            f"Roundtrip failed: {bx,by,vx,vy,py,gs,ku,kd} → {dbx,dby,dvx,dvy,dpy,dgs,dku,dkd}"


def test_physics_all_combos_output():
    """Every combination produces a valid output."""
    count = 0
    for inp, out in generate_all_game_state_samples():
        assert len(inp) == INPUT_SIZE, f"Input length {len(inp)} != {INPUT_SIZE}"
        assert len(out) == OUTPUT_SIZE, f"Output length {len(out)} != {OUTPUT_SIZE}"
        nbx, nby, nvx, nvy, npy, ngs = decode_output(out)
        assert 0 <= nbx < BALL_X_RANGE
        assert 0 <= nby < BALL_Y_RANGE
        assert 0 <= nvx < BALL_V_RANGE
        assert 0 <= nvy < BALL_V_RANGE
        assert 0 <= npy < PADDLE_Y_RANGE
        assert 0 <= ngs < GAME_STATE_RANGE
        count += 1
    expected = (BALL_X_RANGE * BALL_Y_RANGE * BALL_V_RANGE * BALL_V_RANGE *
                PADDLE_Y_RANGE * GAME_STATE_RANGE * KEY_RANGE * KEY_RANGE)
    assert count == expected, f"Generated {count} samples, expected {expected}"


def test_physics_ball_velocity_default():
    """Ball with no keypress and no walls moves in straight line."""
    bx, by, vx, vy, py, gs, ku, kd = 10, 7, 1, 1, 5, 0, 0, 0
    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
    assert nbx == 11, f"Ball should move right: {bx}→{nbx}"
    assert nby == 8, f"Ball should move down: {by}→{nby}"
    assert nvx == 1 and nvy == 1, "Velocity unchanged without bounce"
    assert npy == 5, "Paddle unchanged without keypress"
