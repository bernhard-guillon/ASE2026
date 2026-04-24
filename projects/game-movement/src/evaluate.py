"""
Evaluate movement model quality with exact-match metrics and border-focused breakdown.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import torch

from movement_dataset import ACTIONS, BOARD_SIZE, decode_board_index, load_movement_dataset
from movement_model import create_movement_model


def load_checkpoint(path: str, device: str):
    payload = torch.load(path, map_location=device)
    if isinstance(payload, dict) and "model_state_dict" in payload:
        return payload
    return {"model_state_dict": payload}


def is_border(x: int, y: int) -> bool:
    return x in (0, BOARD_SIZE - 1) or y in (0, BOARD_SIZE - 1)


def is_corner(x: int, y: int) -> bool:
    return x in (0, BOARD_SIZE - 1) and y in (0, BOARD_SIZE - 1)


def main() -> int:
    required = float(sys.argv[1]) if len(sys.argv) > 1 else 0.999
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    ds = load_movement_dataset("movement_dataset.npz")
    x_data = ds["x"].astype(np.float32)
    y_data = ds["y"].astype(np.float32)
    cur_x = ds["cur_x"].astype(np.int64)
    cur_y = ds["cur_y"].astype(np.int64)
    action_id = ds["action_id"].astype(np.int64)
    next_x = ds["next_x"].astype(np.int64)
    next_y = ds["next_y"].astype(np.int64)
    target_idx = np.argmax(y_data, axis=1).astype(np.int64)

    ckpt = load_checkpoint("movement_model.pth", device)
    model = create_movement_model(device=device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    with torch.no_grad():
        logits = model(x_tensor)
        pred_idx = torch.argmax(logits, dim=1).cpu().numpy()

    exact = (pred_idx == target_idx).astype(np.float32)
    overall = float(exact.mean())

    per_action: Dict[str, float] = {}
    for aid, name in enumerate(ACTIONS):
        mask = action_id == aid
        per_action[name] = float(exact[mask].mean()) if np.any(mask) else 0.0

    border_mask = np.array([is_border(int(x), int(y)) for x, y in zip(cur_x, cur_y)], dtype=bool)
    corner_mask = np.array([is_corner(int(x), int(y)) for x, y in zip(cur_x, cur_y)], dtype=bool)

    border_acc = float(exact[border_mask].mean()) if np.any(border_mask) else 0.0
    corner_acc = float(exact[corner_mask].mean()) if np.any(corner_mask) else 0.0

    mismatches = []
    mismatch_idx = np.where(pred_idx != target_idx)[0]
    for idx in mismatch_idx.tolist():
        px, py = decode_board_index(int(pred_idx[idx]), BOARD_SIZE)
        mismatches.append(
            {
                "sample_index": int(idx),
                "x": int(cur_x[idx]),
                "y": int(cur_y[idx]),
                "action_id": int(action_id[idx]),
                "action": ACTIONS[int(action_id[idx])],
                "expected_next_x": int(next_x[idx]),
                "expected_next_y": int(next_y[idx]),
                "predicted_next_x": int(px),
                "predicted_next_y": int(py),
            }
        )

    summary = {
        "required_exact_match": required,
        "overall_exact_match": overall,
        "border_exact_match": border_acc,
        "corner_exact_match": corner_acc,
        "per_action_exact_match": per_action,
        "num_samples": int(len(x_data)),
        "num_mismatches": int(len(mismatches)),
    }

    Path("movement_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path("movement_mismatches.json").write_text(json.dumps(mismatches, indent=2), encoding="utf-8")

    print("Evaluation summary:")
    print(json.dumps(summary, indent=2))

    passed = (
        overall >= required
        and border_acc >= required
        and corner_acc >= required
        and len(mismatches) == 0
    )
    if passed:
        print("✓ Movement model evaluation PASSED")
        return 0
    print("✗ Movement model evaluation FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
