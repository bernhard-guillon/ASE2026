"""
Train Model B (Counter Model).

Trains a neural network to predict counter state transitions.

Input: encoded counter state (11) + hit_wall bit (1) = 12
Output: encoded next counter state (11)
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from generate_counter_dataset import generate_counter_dataset
from counter_model import create_counter_model, COUNTER_INPUT_SIZE, COUNTER_OUTPUT_SIZE


def set_seed(seed: int = 1337) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def counter_loss_fn() -> nn.Module:
    """
    Create a loss function for counter model.
    
    The output consists of:
    - count: 10 one-hot buckets (indices 0-9)
    - stop: 1 binary value (index 10)
    
    We use CrossEntropyLoss for count and BCEWithLogitsLoss for stop.
    """
    return nn.ModuleDict({
        "count": nn.CrossEntropyLoss(),
        "stop": nn.BCEWithLogitsLoss(),
    })


def compute_counter_loss(
    predictions: torch.Tensor,
    targets: torch.Tensor,
    loss_fns: nn.ModuleDict,
) -> torch.Tensor:
    """
    Compute loss for counter model.
    
    Args:
        predictions: Model output tensor of shape (batch, 11)
        targets: Target tensor of shape (batch, 11)
        loss_fns: Dictionary of loss functions for each component
    
    Returns:
        Total scalar loss
    """
    # Split predictions and targets
    # count: indices 0-9
    pred_count = predictions[:, :10]
    target_count = targets[:, :10]
    
    # stop: index 10
    pred_stop = predictions[:, 10:]
    target_stop = targets[:, 10:]
    
    # Convert one-hot count targets to class indices
    target_count_idx = torch.argmax(target_count, dim=1)
    
    # Compute losses
    loss_count = loss_fns["count"](pred_count, target_count_idx)
    loss_stop = loss_fns["stop"](pred_stop, target_stop)
    
    # Weighted sum - both components equally weighted
    total_loss = loss_count + loss_stop
    
    return total_loss


def exact_match_counter(predictions: torch.Tensor, targets: torch.Tensor) -> float:
    """
    Compute exact match accuracy for counter model.
    
    Both count and stop must match exactly.
    """
    # Convert predictions to class indices
    pred_count_idx = torch.argmax(predictions[:, :10], dim=1)
    pred_stop = (predictions[:, 10:] > 0).float().squeeze()
    
    # Convert targets to class indices
    target_count_idx = torch.argmax(targets[:, :10], dim=1)
    target_stop = targets[:, 10:].squeeze()
    
    # Check all components match
    match_count = (pred_count_idx == target_count_idx).float()
    match_stop = (pred_stop == target_stop).float()
    
    all_match = match_count * match_stop
    return float(all_match.mean().item())


def main() -> int:
    set_seed()

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    learning_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-3

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("1) Generating counter dataset...")
    arrays = generate_counter_dataset("counter_dataset.npz", "counter_transitions.json")
    x_data = arrays["x"]
    y_data = arrays["y"]
    print(f"   Samples: {len(x_data)}")
    print(f"   Input shape: {x_data.shape}")
    print(f"   Output shape: {y_data.shape}")

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y_data, dtype=torch.float32, device=device)
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("2) Training counter model...")
    model = create_counter_model(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fns = counter_loss_fn()
    loss_fns.to(device)

    metrics = {
        "epochs": [],
        "train_loss": [],
        "exact_match": [],
    }

    perfect_streak = 0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in dataloader:
            logits = model(batch_x)
            loss = compute_counter_loss(logits, batch_y, loss_fns)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            full_logits = model(x_tensor)
            acc = exact_match_counter(full_logits, y_tensor)

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
        if perfect_streak >= 5:
            print("   Early stop: near-perfect exact-match sustained.")
            break

    print("3) Saving artifacts...")
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "input_size": COUNTER_INPUT_SIZE,
        "hidden_size": 64,
        "output_size": COUNTER_OUTPUT_SIZE,
    }
    torch.save(checkpoint, "counter_model.pth")
    Path("counter_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    final_acc = metrics["exact_match"][-1] if metrics["exact_match"] else 0.0
    print(f"Training complete. Final exact match: {final_acc*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
