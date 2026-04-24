"""
Train the single-player movement model.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from movement_dataset import ACTIONS, BOARD_SIZE, generate_movement_dataset
from movement_model import create_movement_model


def set_seed(seed: int = 1337) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def exact_match(logits: torch.Tensor, target_idx: torch.Tensor) -> float:
    pred_idx = torch.argmax(logits, dim=1)
    return float((pred_idx == target_idx).float().mean().item())


def main() -> int:
    set_seed()

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    learning_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-3

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("1) Generating movement dataset...")
    arrays = generate_movement_dataset("movement_dataset.npz", "movement_transitions.json")
    x_data = arrays["x"]
    y_data = arrays["y"]
    target_idx = np.argmax(y_data, axis=1).astype(np.int64)
    print(f"   Samples: {len(x_data)} (expected {BOARD_SIZE*BOARD_SIZE*len(ACTIONS)})")
    print(f"   Input shape: {x_data.shape}")
    print(f"   Target shape: {y_data.shape}")

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    idx_tensor = torch.tensor(target_idx, dtype=torch.long, device=device)
    dataset = TensorDataset(x_tensor, idx_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("2) Training model...")
    model = create_movement_model(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = torch.nn.CrossEntropyLoss()

    metrics = {
        "epochs": [],
        "train_loss": [],
        "exact_match": [],
    }

    perfect_streak = 0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_idx in dataloader:
            logits = model(batch_x)
            loss = criterion(logits, batch_idx)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            full_logits = model(x_tensor)
            acc = exact_match(full_logits, idx_tensor)

        avg_loss = total_loss / max(1, len(dataloader))
        metrics["epochs"].append(epoch)
        metrics["train_loss"].append(avg_loss)
        metrics["exact_match"].append(acc)

        if epoch == 1 or epoch % 10 == 0:
            print(f"   Epoch {epoch:3d}/{epochs}: loss={avg_loss:.6f}, exact={acc*100:.2f}%")

        if acc >= 0.9999:
            perfect_streak += 1
        else:
            perfect_streak = 0
        if perfect_streak >= 10:
            print("   Early stop: perfect exact-match sustained.")
            break

    print("3) Saving artifacts...")
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "input_size": 405,
        "hidden_size": 128,
        "output_size": 400,
        "board_size": BOARD_SIZE,
        "actions": list(ACTIONS),
    }
    torch.save(checkpoint, "movement_model.pth")
    Path("movement_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    final_acc = metrics["exact_match"][-1] if metrics["exact_match"] else 0.0
    print(f"Training complete. Final exact match: {final_acc*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
