"""
Test reference squash renderer function.
Verifies correct pixel output for all state combinations.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from squash_renderer import (
    W, H, OUTPUT_PIXELS, BALL_X_RANGE, BALL_Y_RANGE,
    PADDLE_Y_RANGE, GAME_STATE_RANGE, PADDLE_HEIGHT, PADDLE_WIDTH,
    render, generate_all_renderer_samples,
)


def _active_pixels(pixels):
    return [i for i, p in enumerate(pixels) if p > 0.5]


def test_render_walls_present():
    """Walls (all 4 edges) are always present when game is live."""
    pixels = render(10, 7, 5, 0)
    active = set(_active_pixels(pixels))
    for y in range(H):
        assert y * W + 0 in active, f"Left wall pixel ({0},{y}) missing"
        assert y * W + (W - 1) in active, f"Right wall pixel ({W-1},{y}) missing"
    for x in range(W):
        assert 0 * W + x in active, f"Top wall pixel ({x},0) missing"
        assert (H - 1) * W + x in active, f"Bottom wall pixel ({x},{H-1}) missing"


def test_render_ball_at_position():
    """Ball is drawn at the correct (bx, by) position."""
    bx, by = 7, 4
    pixels = render(bx, by, 5, 0)
    active = set(_active_pixels(pixels))
    assert (by * W + bx) in active, f"Ball pixel ({bx},{by}) missing"
    assert (by * W + bx + 1) in active, f"Ball pixel ({bx+1},{by}) missing"
    assert ((by + 1) * W + bx) in active, f"Ball pixel ({bx},{by+1}) missing"
    assert ((by + 1) * W + bx + 1) in active, f"Ball pixel ({bx+1},{by+1}) missing"


def test_render_paddle_at_position():
    """Paddle is drawn at the correct py position."""
    py = 3
    pixels = render(10, 7, py, 0)
    active = set(_active_pixels(pixels))
    for dy in range(PADDLE_HEIGHT):
        for dx in range(PADDLE_WIDTH):
            assert ((py + dy) * W + 1 + dx) in active, \
                f"Paddle pixel ({1+dx},{py+dy}) missing"


def test_render_ball_near_wall():
    """Ball at edge doesn't break anything (no crash, non-negative indices)."""
    pixels = render(0, 0, 5, 0)
    assert len(pixels) == OUTPUT_PIXELS
    assert sum(1 for p in pixels if p > 0.5) > 0


def test_render_game_over():
    """Game over state produces different output than live."""
    live_pixels = render(10, 7, 5, 0)
    dead_pixels = render(10, 7, 5, 1)
    live_active = set(_active_pixels(live_pixels))
    dead_active = set(_active_pixels(dead_pixels))
    assert dead_active != live_active, "Game over should produce different pixels"


def test_render_all_positions_distinct():
    """Different ball positions produce different pixel outputs."""
    p1 = render(5, 5, 5, 0)
    p2 = render(6, 5, 5, 0)
    assert p1 != p2, "Different ball positions should differ"


def test_render_all_combos_valid():
    """Every renderer combination produces valid output."""
    count = 0
    for inp, pixels in generate_all_renderer_samples():
        assert len(inp) == 48, f"Input length {len(inp)} != 48"
        assert len(pixels) == OUTPUT_PIXELS, f"Output length {len(pixels)} != {OUTPUT_PIXELS}"
        for p in pixels:
            assert 0.0 <= p <= 1.0, f"Pixel value {p} out of range"
        count += 1
    expected = BALL_X_RANGE * BALL_Y_RANGE * PADDLE_Y_RANGE * GAME_STATE_RANGE
    assert count == expected, f"Generated {count} samples, expected {expected}"
