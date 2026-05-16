"""
Train Model A (Physics Model).

Trains a neural network to predict physics state transitions and hit_wall pulses.

Input: encoded physics state (46) + stop bit (1) = 47
Output: encoded next physics state (46) + hit_wall (1) = 47
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

from dual_model_contract import GRID_SIZE
from generate_physics_dataset import generate_physics_dataset
from physics_model import create_physics_model, PHYSICS_INPUT_SIZE, PHYSICS_OUTPUT_SIZE


def set_seed(seed: int = 1337) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def physics_loss_fn() -> nn.Module:
    """
    Create a loss function for physics model.
    
    The output consists of multiple one-hot encoded groups plus a binary hit_wall:
    - ball_x: 20 one-hot buckets (indices 0-19)
    - ball_y: 20 one-hot buckets (indices 20-39)
    - vel_x: 3 one-hot buckets (indices 40-42)
    - vel_y: 3 one-hot buckets (indices 43-45)
    - hit_wall: 1 binary value (index 46)
    
    We use CrossEntropyLoss for each one-hot group and BCEWithLogitsLoss for hit_wall.
    """
    return nn.ModuleDict({
        "ball_x": nn.CrossEntropyLoss(),
        "ball_y": nn.CrossEntropyLoss(),
        "vel_x": nn.CrossEntropyLoss(),
        "vel_y": nn.CrossEntropyLoss(),
        "hit_wall": nn.BCEWithLogitsLoss(),
    })


def compute_physics_loss(
    predictions: torch.Tensor,
    targets: torch.Tensor,
    loss_fns: nn.ModuleDict,
) -> torch.Tensor:
    """
    Compute loss for physics model.
    
    Args:
        predictions: Model output tensor of shape (batch, 47)
        targets: Target tensor of shape (batch, 47)
        loss_fns: Dictionary of loss functions for each component
    
    Returns:
        Total scalar loss
    """
    batch_size = predictions.shape[0]
    
    # Split predictions and targets into component groups
    # ball_x: indices 0-19
    pred_ball_x = predictions[:, :GRID_SIZE]
    target_ball_x = targets[:, :GRID_SIZE]
    
    # ball_y: indices 20-39
    pred_ball_y = predictions[:, GRID_SIZE:2*GRID_SIZE]
    target_ball_y = targets[:, GRID_SIZE:2*GRID_SIZE]
    
    # vel_x: indices 40-42
    pred_vel_x = predictions[:, 2*GRID_SIZE:2*GRID_SIZE+3]
    target_vel_x = targets[:, 2*GRID_SIZE:2*GRID_SIZE+3]
    
    # vel_y: indices 43-45
    pred_vel_y = predictions[:, 2*GRID_SIZE+3:2*GRID_SIZE+6]
    target_vel_y = targets[:, 2*GRID_SIZE+3:2*GRID_SIZE+6]
    
    # hit_wall: index 46
    pred_hit_wall = predictions[:, -1:]
    target_hit_wall = targets[:, -1:]
    
    # Convert one-hot targets to class indices for CrossEntropyLoss
    target_ball_x_idx = torch.argmax(target_ball_x, dim=1)
    target_ball_y_idx = torch.argmax(target_ball_y, dim=1)
    target_vel_x_idx = torch.argmax(target_vel_x, dim=1)
    target_vel_y_idx = torch.argmax(target_vel_y, dim=1)
    
    # Compute losses for each component
    loss_ball_x = loss_fns["ball_x"](pred_ball_x, target_ball_x_idx)
    loss_ball_y = loss_fns["ball_y"](pred_ball_y, target_ball_y_idx)
    loss_vel_x = loss_fns["vel_x"](pred_vel_x, target_vel_x_idx)
    loss_vel_y = loss_fns["vel_y"](pred_vel_y, target_vel_y_idx)
    loss_hit_wall = loss_fns["hit_wall"](pred_hit_wall, target_hit_wall)
    
    # Weighted sum - all components equally weighted
    total_loss = loss_ball_x + loss_ball_y + loss_vel_x + loss_vel_y + loss_hit_wall
    
    return total_loss


def exact_match_physics(predictions: torch.Tensor, targets: torch.Tensor) -> float:
    """
    Compute exact match accuracy for physics model.
    
    All components (ball_x, ball_y, vel_x, vel_y, hit_wall) must match exactly.
    """
    # Convert predictions to class indices for one-hot parts
    pred_ball_x_idx = torch.argmax(predictions[:, :GRID_SIZE], dim=1)
    pred_ball_y_idx = torch.argmax(predictions[:, GRID_SIZE:2*GRID_SIZE], dim=1)
    pred_vel_x_idx = torch.argmax(predictions[:, 2*GRID_SIZE:2*GRID_SIZE+3], dim=1)
    pred_vel_y_idx = torch.argmax(predictions[:, 2*GRID_SIZE+3:2*GRID_SIZE+6], dim=1)
    pred_hit_wall = (predictions[:, -1:] > 0).float().squeeze()
    
    # Convert targets to class indices
    target_ball_x_idx = torch.argmax(targets[:, :GRID_SIZE], dim=1)
    target_ball_y_idx = torch.argmax(targets[:, GRID_SIZE:2*GRID_SIZE], dim=1)
    target_vel_x_idx = torch.argmax(targets[:, 2*GRID_SIZE:2*GRID_SIZE+3], dim=1)
    target_vel_y_idx = torch.argmax(targets[:, 2*GRID_SIZE+3:2*GRID_SIZE+6], dim=1)
    target_hit_wall = targets[:, -1:].squeeze()
    
    # Check all components match
    match_ball_x = (pred_ball_x_idx == target_ball_x_idx).float()
    match_ball_y = (pred_ball_y_idx == target_ball_y_idx).float()
    match_vel_x = (pred_vel_x_idx == target_vel_x_idx).float()
    match_vel_y = (pred_vel_y_idx == target_vel_y_idx).float()
    match_hit_wall = (pred_hit_wall == target_hit_wall).float()
    
    all_match = match_ball_x * match_ball_y * match_vel_x * match_vel_y * match_hit_wall
    return float(all_match.mean().item())


def main() -> int:
    set_seed()

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    learning_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-3

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("1) Generating physics dataset...")
    arrays = generate_physics_dataset("physics_dataset.npz", "physics_transitions.json")
    x_data = arrays["x"]
    y_data = arrays["y"]
    print(f"   Samples: {len(x_data)}")
    print(f"   Input shape: {x_data.shape}")
    print(f"   Output shape: {y_data.shape}")

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y_data, dtype=torch.float32, device=device)
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("2) Training physics model...")
    model = create_physics_model(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fns = physics_loss_fn()
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
            loss = compute_physics_loss(logits, batch_y, loss_fns)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            full_logits = model(x_tensor)
            acc = exact_match_physics(full_logits, y_tensor)

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
        "input_size": PHYSICS_INPUT_SIZE,
        "hidden_size": 128,
        "output_size": PHYSICS_OUTPUT_SIZE,
        "grid_size": GRID_SIZE,
    }
    torch.save(checkpoint, "physics_model.pth")
    Path("physics_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    final_acc = metrics["exact_match"][-1] if metrics["exact_match"] else 0.0
    print(f"Training complete. Final exact match: {final_acc*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
