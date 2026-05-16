"""
Generate and load squash/Pong-style transitions for a 20x20 framebuffer.

Input format:
- current framebuffer state (400 floats, 0/1)
- key input one-hot (255 floats, same key-code channel style as char-generation)

Output format:
- next framebuffer state (400 floats, 0/1)
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


BOARD_SIZE = 20
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE
PADDLE_HEIGHT = 3
PADDLE_X = BOARD_SIZE - 1
KEY_DIM = 255

KEY_UP = "j"
KEY_DOWN = "k"
KEY_STAY = " "
KEYS = (KEY_UP, KEY_DOWN, KEY_STAY)
KEY_TO_ACTION = {
    KEY_UP: -1,
    KEY_DOWN: 1,
    KEY_STAY: 0,
}


@dataclass
class SquashState:
    ball_x: int
    ball_y: int
    ball_dx: int
    ball_dy: int
    paddle_top: int
    game_over: bool = False


def _clamp_paddle(top: int) -> int:
    return max(0, min(BOARD_SIZE - PADDLE_HEIGHT, top))


def _random_start_direction(rng: random.Random) -> Tuple[int, int]:
    # Ball always launches to the right from x=0, random vertical component.
    return 1, rng.choice([-1, 0, 1])


def make_initial_state(rng: random.Random) -> SquashState:
    dx, dy = _random_start_direction(rng)
    return SquashState(
        ball_x=0,
        ball_y=BOARD_SIZE // 2,
        ball_dx=dx,
        ball_dy=dy,
        paddle_top=(BOARD_SIZE // 2) - (PADDLE_HEIGHT // 2),
        game_over=False,
    )


def step_oracle(state: SquashState, action: int) -> SquashState:
    if state.game_over:
        return state

    paddle_top = _clamp_paddle(state.paddle_top + action)

    next_x = state.ball_x + state.ball_dx
    next_y = state.ball_y + state.ball_dy
    ball_dx = state.ball_dx
    ball_dy = state.ball_dy

    # Top/bottom reflections.
    if next_y < 0 or next_y >= BOARD_SIZE:
        ball_dy *= -1
        next_y = state.ball_y + ball_dy

    # Left reflection.
    if next_x < 0:
        ball_dx = 1
        next_x = state.ball_x + ball_dx

    # Right side: paddle hit or loss.
    if next_x >= PADDLE_X:
        if paddle_top <= next_y < paddle_top + PADDLE_HEIGHT:
            ball_dx = -1
            next_x = state.ball_x + ball_dx
        else:
            return SquashState(
                ball_x=PADDLE_X,
                ball_y=max(0, min(BOARD_SIZE - 1, next_y)),
                ball_dx=ball_dx,
                ball_dy=ball_dy,
                paddle_top=paddle_top,
                game_over=True,
            )

    return SquashState(
        ball_x=next_x,
        ball_y=next_y,
        ball_dx=ball_dx,
        ball_dy=ball_dy,
        paddle_top=paddle_top,
        game_over=False,
    )


def render_frame(state: SquashState) -> np.ndarray:
    frame = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.float32)
    for y in range(state.paddle_top, state.paddle_top + PADDLE_HEIGHT):
        frame[y, PADDLE_X] = 1.0
    frame[state.ball_y, state.ball_x] = 1.0
    return frame.reshape(-1)


def key_to_onehot(key_char: str) -> np.ndarray:
    if len(key_char) != 1:
        raise ValueError(f"Expected single key char, got '{key_char}'")
    key_code = ord(key_char)
    if not (0 <= key_code < KEY_DIM):
        raise ValueError(f"Key code {key_code} out of [0, {KEY_DIM - 1}]")
    vec = np.zeros(KEY_DIM, dtype=np.float32)
    vec[key_code] = 1.0
    return vec


def generate_squash_dataset(
    npz_path: str | Path = "squash_dataset.npz",
    json_path: str | Path = "squash_transitions.json",
    episodes: int = 600,
    steps_per_episode: int = 120,
    seed: int = 1337,
) -> Dict[str, np.ndarray]:
    npz_path = Path(npz_path)
    json_path = Path(json_path)

    rng = random.Random(seed)

    x_inputs: List[np.ndarray] = []
    y_targets: List[np.ndarray] = []
    key_codes: List[int] = []
    actions: List[int] = []
    game_over_flags: List[int] = []
    episode_ids: List[int] = []
    step_ids: List[int] = []

    json_rows = []

    for episode in range(episodes):
        state = make_initial_state(rng)
        for step in range(steps_per_episode):
            key_char = rng.choices(KEYS, weights=[0.25, 0.25, 0.5], k=1)[0]
            action = KEY_TO_ACTION[key_char]

            cur_frame = render_frame(state)
            next_state = step_oracle(state, action)
            next_frame = render_frame(next_state)

            x_inputs.append(np.concatenate([cur_frame, key_to_onehot(key_char)]).astype(np.float32))
            y_targets.append(next_frame.astype(np.float32))
            key_codes.append(ord(key_char))
            actions.append(action)
            game_over_flags.append(1 if next_state.game_over else 0)
            episode_ids.append(episode)
            step_ids.append(step)

            json_rows.append(
                {
                    "episode": episode,
                    "step": step,
                    "key": key_char,
                    "key_code": ord(key_char),
                    "action": action,
                    "ball_x": state.ball_x,
                    "ball_y": state.ball_y,
                    "ball_dx": state.ball_dx,
                    "ball_dy": state.ball_dy,
                    "paddle_top": state.paddle_top,
                    "next_ball_x": next_state.ball_x,
                    "next_ball_y": next_state.ball_y,
                    "next_ball_dx": next_state.ball_dx,
                    "next_ball_dy": next_state.ball_dy,
                    "next_paddle_top": next_state.paddle_top,
                    "game_over": next_state.game_over,
                }
            )

            # Start fresh trajectory after miss.
            if next_state.game_over:
                break
            state = next_state

    arrays = {
        "x": np.asarray(x_inputs, dtype=np.float32),
        "y": np.asarray(y_targets, dtype=np.float32),
        "key_code": np.asarray(key_codes, dtype=np.int16),
        "action": np.asarray(actions, dtype=np.int8),
        "game_over": np.asarray(game_over_flags, dtype=np.int8),
        "episode": np.asarray(episode_ids, dtype=np.int32),
        "step": np.asarray(step_ids, dtype=np.int16),
        "board_size": np.asarray([BOARD_SIZE], dtype=np.int16),
    }
    np.savez(npz_path, **arrays)

    payload = {
        "board_size": BOARD_SIZE,
        "paddle_height": PADDLE_HEIGHT,
        "paddle_x": PADDLE_X,
        "keys": list(KEYS),
        "episodes": episodes,
        "steps_per_episode": steps_per_episode,
        "seed": seed,
        "num_samples": int(arrays["x"].shape[0]),
        "samples": json_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return arrays


def load_squash_dataset(npz_path: str | Path = "squash_dataset.npz") -> Dict[str, np.ndarray]:
    payload = np.load(npz_path)
    return {k: payload[k] for k in payload.files}
