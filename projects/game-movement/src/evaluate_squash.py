"""
Evaluate squash world model on generated dataset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

from squash_dataset import generate_squash_dataset, load_squash_dataset
from squash_model import create_squash_model


def load_checkpoint(path: str, device: str):
    payload = torch.load(path, map_location=device)
    if isinstance(payload, dict) and "model_state_dict" in payload:
        return payload
    return {"model_state_dict": payload}


def main() -> int:
    required_exact = float(sys.argv[1]) if len(sys.argv) > 1 else 0.80
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    if not Path("squash_dataset.npz").exists():
        generate_squash_dataset("squash_dataset.npz", "squash_transitions.json")
    ds = load_squash_dataset("squash_dataset.npz")

    x_data = ds["x"].astype(np.float32)
    y_data = ds["y"].astype(np.float32)
    game_over = ds["game_over"].astype(np.int8)
    key_codes = ds["key_code"].astype(np.int16)

    ckpt = load_checkpoint("squash_model.pth", device)
    model = create_squash_model(device=device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y_data, dtype=torch.float32, device=device)
    with torch.no_grad():
        logits = model(x_tensor)
        probs = torch.sigmoid(logits)
        pred = (probs >= 0.5).float()

    per_sample_exact = (pred == y_tensor).all(dim=1).float().cpu().numpy()
    overall_exact = float(per_sample_exact.mean())
    pixel_acc = float((pred == y_tensor).float().mean().item())

    terminal_mask = game_over == 1
    terminal_exact = float(per_sample_exact[terminal_mask].mean()) if np.any(terminal_mask) else 0.0
    non_terminal_exact = float(per_sample_exact[~terminal_mask].mean()) if np.any(~terminal_mask) else 0.0

    j_mask = key_codes == ord("j")
    k_mask = key_codes == ord("k")
    stay_mask = key_codes == ord(" ")
    per_key = {
        "j_up_exact": float(per_sample_exact[j_mask].mean()) if np.any(j_mask) else 0.0,
        "k_down_exact": float(per_sample_exact[k_mask].mean()) if np.any(k_mask) else 0.0,
        "stay_exact": float(per_sample_exact[stay_mask].mean()) if np.any(stay_mask) else 0.0,
    }

    mismatch_idx = np.where(per_sample_exact < 0.5)[0]
    mismatches = [{"sample_index": int(i), "key_code": int(key_codes[i]), "game_over": int(game_over[i])} for i in mismatch_idx[:300]]

    summary = {
        "required_frame_exact_match": required_exact,
        "overall_frame_exact_match": overall_exact,
        "pixel_accuracy": pixel_acc,
        "terminal_frame_exact_match": terminal_exact,
        "non_terminal_frame_exact_match": non_terminal_exact,
        "per_key_exact_match": per_key,
        "num_samples": int(len(x_data)),
        "num_mismatches": int(len(mismatch_idx)),
    }
    Path("squash_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path("squash_mismatches.json").write_text(json.dumps(mismatches, indent=2), encoding="utf-8")

    print("Evaluation summary:")
    print(json.dumps(summary, indent=2))

    if overall_exact >= required_exact:
        print("✓ Squash model evaluation PASSED")
        return 0
    print("✗ Squash model evaluation FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
