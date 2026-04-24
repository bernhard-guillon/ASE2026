"""
Generate and load deterministic player-movement transition data for a 20x20 board.

State: one active player cell ("#") on the board.
Action space: up, down, left, right, stay.
Transition: move one step with strict boundary clamp.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np


BOARD_SIZE = 20
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE
ACTIONS = ("up", "down", "left", "right", "stay")
ACTION_TO_ID = {name: idx for idx, name in enumerate(ACTIONS)}

_ACTION_DELTAS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
    "stay": (0, 0),
}


@dataclass(frozen=True)
class Transition:
    x: int
    y: int
    action_id: int
    action_name: str
    next_x: int
    next_y: int


def clamp_position(x: int, y: int, board_size: int = BOARD_SIZE) -> Tuple[int, int]:
    return max(0, min(board_size - 1, x)), max(0, min(board_size - 1, y))


def transition_oracle(x: int, y: int, action_name: str, board_size: int = BOARD_SIZE) -> Tuple[int, int]:
    if action_name not in _ACTION_DELTAS:
        raise ValueError(f"Unsupported action '{action_name}'. Expected one of: {ACTIONS}")
    dx, dy = _ACTION_DELTAS[action_name]
    return clamp_position(x + dx, y + dy, board_size)


def encode_board(x: int, y: int, board_size: int = BOARD_SIZE) -> np.ndarray:
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise ValueError(f"Position out of bounds: ({x}, {y}) for board {board_size}x{board_size}")
    board = np.zeros(board_size * board_size, dtype=np.float32)
    board[y * board_size + x] = 1.0
    return board


def decode_board_index(index: int, board_size: int = BOARD_SIZE) -> Tuple[int, int]:
    if not (0 <= index < board_size * board_size):
        raise ValueError(f"Board index out of range: {index}")
    y, x = divmod(index, board_size)
    return x, y


def encode_action(action_id: int) -> np.ndarray:
    if not (0 <= action_id < len(ACTIONS)):
        raise ValueError(f"Action id out of range: {action_id}")
    vec = np.zeros(len(ACTIONS), dtype=np.float32)
    vec[action_id] = 1.0
    return vec


def iter_all_transitions(board_size: int = BOARD_SIZE) -> Iterable[Transition]:
    for y in range(board_size):
        for x in range(board_size):
            for action_id, action_name in enumerate(ACTIONS):
                next_x, next_y = transition_oracle(x, y, action_name, board_size)
                yield Transition(
                    x=x,
                    y=y,
                    action_id=action_id,
                    action_name=action_name,
                    next_x=next_x,
                    next_y=next_y,
                )


def generate_movement_dataset(
    npz_path: str | Path = "movement_dataset.npz",
    json_path: str | Path = "movement_transitions.json",
    board_size: int = BOARD_SIZE,
) -> Dict[str, np.ndarray]:
    npz_path = Path(npz_path)
    json_path = Path(json_path)

    inputs: List[np.ndarray] = []
    targets: List[np.ndarray] = []
    cur_x: List[int] = []
    cur_y: List[int] = []
    action_ids: List[int] = []
    next_xs: List[int] = []
    next_ys: List[int] = []

    json_rows = []

    for t in iter_all_transitions(board_size):
        cur_board = encode_board(t.x, t.y, board_size)
        action_vec = encode_action(t.action_id)
        next_board = encode_board(t.next_x, t.next_y, board_size)

        inputs.append(np.concatenate([cur_board, action_vec]).astype(np.float32))
        targets.append(next_board.astype(np.float32))
        cur_x.append(t.x)
        cur_y.append(t.y)
        action_ids.append(t.action_id)
        next_xs.append(t.next_x)
        next_ys.append(t.next_y)

        json_rows.append(
            {
                "x": t.x,
                "y": t.y,
                "action_id": t.action_id,
                "action": t.action_name,
                "next_x": t.next_x,
                "next_y": t.next_y,
                "state_index": int(t.y * board_size + t.x),
                "next_state_index": int(t.next_y * board_size + t.next_x),
            }
        )

    x_data = np.asarray(inputs, dtype=np.float32)
    y_data = np.asarray(targets, dtype=np.float32)

    arrays = {
        "x": x_data,
        "y": y_data,
        "cur_x": np.asarray(cur_x, dtype=np.int16),
        "cur_y": np.asarray(cur_y, dtype=np.int16),
        "action_id": np.asarray(action_ids, dtype=np.int16),
        "next_x": np.asarray(next_xs, dtype=np.int16),
        "next_y": np.asarray(next_ys, dtype=np.int16),
        "board_size": np.asarray([board_size], dtype=np.int16),
    }

    np.savez(npz_path, **arrays)

    json_payload = {
        "board_size": board_size,
        "actions": list(ACTIONS),
        "samples": json_rows,
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    return arrays


def load_movement_dataset(npz_path: str | Path = "movement_dataset.npz") -> Dict[str, np.ndarray]:
    payload = np.load(npz_path)
    return {k: payload[k] for k in payload.files}
