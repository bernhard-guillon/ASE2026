"""
Train squash world model:
input (frame + key one-hot) -> next 20x20 framebuffer.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from squash_dataset import generate_squash_dataset
from squash_model import create_squash_model


def set_seed(seed: int = 1337) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def frame_exact_match(logits: torch.Tensor, target: torch.Tensor) -> float:
    pred = (torch.sigmoid(logits) >= 0.5).float()
    per_sample_exact = (pred == target).all(dim=1).float()
    return float(per_sample_exact.mean().item())


def pixel_accuracy(logits: torch.Tensor, target: torch.Tensor) -> float:
    pred = (torch.sigmoid(logits) >= 0.5).float()
    return float((pred == target).float().mean().item())


def main() -> int:
    set_seed()

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 128
    learning_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-3
    episodes = int(sys.argv[4]) if len(sys.argv) > 4 else 600
    steps_per_episode = int(sys.argv[5]) if len(sys.argv) > 5 else 120

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("1) Generating squash dataset...")
    arrays = generate_squash_dataset(
        npz_path="squash_dataset.npz",
        json_path="squash_transitions.json",
        episodes=episodes,
        steps_per_episode=steps_per_episode,
        seed=1337,
    )
    x_data = arrays["x"]
    y_data = arrays["y"]
    print(f"   Samples: {len(x_data)}")
    print(f"   Input shape: {x_data.shape}")
    print(f"   Target shape: {y_data.shape}")

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y_data, dtype=torch.float32, device=device)
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("2) Training squash model...")
    model = create_squash_model(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = torch.nn.BCEWithLogitsLoss()

    metrics = {
        "epochs": [],
        "train_loss": [],
        "frame_exact_match": [],
        "pixel_accuracy": [],
    }

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in dataloader:
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            full_logits = model(x_tensor)
            exact = frame_exact_match(full_logits, y_tensor)
            pix_acc = pixel_accuracy(full_logits, y_tensor)

        avg_loss = total_loss / max(1, len(dataloader))
        metrics["epochs"].append(epoch)
        metrics["train_loss"].append(avg_loss)
        metrics["frame_exact_match"].append(exact)
        metrics["pixel_accuracy"].append(pix_acc)

        if epoch == 1 or epoch % 5 == 0:
            print(
                f"   Epoch {epoch:3d}/{epochs}: loss={avg_loss:.6f}, "
                f"frame_exact={exact*100:.2f}%, pixel_acc={pix_acc*100:.2f}%"
            )

    print("3) Saving artifacts...")
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "input_size": 655,
        "hidden_size": 512,
        "output_size": 400,
        "key_mapping": {"j": ord("j"), "k": ord("k"), "stay": ord(" ")},
    }
    torch.save(checkpoint, "squash_model.pth")
    Path("squash_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    final_exact = metrics["frame_exact_match"][-1] if metrics["frame_exact_match"] else 0.0
    final_pix = metrics["pixel_accuracy"][-1] if metrics["pixel_accuracy"] else 0.0
    print(
        f"Training complete. Final frame exact match: {final_exact*100:.2f}% | "
        f"pixel accuracy: {final_pix*100:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
