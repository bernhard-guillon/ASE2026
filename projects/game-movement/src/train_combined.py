"""
Train Combined Model for Dual-Model Squash Control Chain.

This trains a SINGLE neural network to replicate the behavior of the dual-model
chain (physics + counter). The training data is generated using the DETERMINISTIC
oracles, ensuring the network learns the correct behavior.

Input: framebuffer (400 normalized cells)
Output: next framebuffer (400 normalized cells)

This approach (Option 4a) provides a single-model interface compatible with the
emulator, while the actual behavior is learned from the clean dual-model oracles.
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

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    CounterState,
    default_physics_state,
    default_counter_state,
)
from chain_integrator import simulate_chain_oracle, simulate_chain
from deterministic_renderer import render_frame_compact
from combined_model import create_combined_model


def set_seed(seed: int = 1337) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def frame_to_tensor(frame_str: str) -> np.ndarray:
    """
    Convert a compact frame string to a normalized tensor.
    
    Character to value mapping (designed to avoid overlap):
    - ' ' (space): 0.0 (empty)
    - '#' (wall): 0.2 (static element - low value)
    - '0'-'9' (counter): 0.3 + digit*0.06 (0.30, 0.36, 0.42, ..., 0.84)
    - 'o' (ball): 1.0 (active element - highest value)
    
    Ranges:
    - empty: [0.0, 0.15)
    - wall: [0.15, 0.25)
    - counter: [0.25, 0.90) - 10 distinct values
    - ball: [0.90, 1.0]
    
    This ensures no overlap between categories.
    """
    frame_str = frame_str.replace('\n', '')
    assert len(frame_str) == GRID_SIZE * GRID_SIZE
    
    result = np.zeros(GRID_SIZE * GRID_SIZE, dtype=np.float32)
    
    for i, char in enumerate(frame_str):
        if char == ' ':
            result[i] = 0.0
        elif char == '#':
            result[i] = 0.2
        elif char == 'o':
            result[i] = 1.0
        elif char in '0123456789':
            digit = int(char)
            result[i] = 0.3 + digit * 0.06  # 0.30, 0.36, 0.42, 0.48, 0.54, 0.60, 0.66, 0.72, 0.78, 0.84
        else:
            result[i] = 0.0
    
    return result


def tensor_to_frame(tensor: np.ndarray) -> str:
    """
    Convert a tensor back to a compact frame string.
    
    Uses the same encoding as frame_to_tensor:
    - 0.0: ' '
    - 0.2: '#'
    - 0.3 + digit*0.06: '0'-'9'
    - 1.0: 'o'
    """
    tensor = np.asarray(tensor, dtype=np.float32)
    result = []
    
    for val in tensor:
        if val >= 0.90:
            result.append('o')
        elif val >= 0.25:
            # Counter digit - find closest
            digit = int((val - 0.3) / 0.06 + 0.5)
            digit = max(0, min(9, digit))
            result.append(str(digit))
        elif val >= 0.15:
            result.append('#')
        else:
            result.append(' ')
    
    return ''.join(result)


def generate_combined_dataset(
    npz_path: str | Path = "combined_dataset.npz",
    json_path: str | Path = "combined_transitions.json",
    num_trajectories: int = 100,
    steps_per_trajectory: int = 100,
    seed: int = 42,
) -> dict:
    """
    Generate training data using the dual-model oracle chain.
    
    Creates (input_frame, output_frame) pairs where:
    - input_frame: current framebuffer
    - output_frame: next framebuffer after one chain step
    
    The oracle ensures perfect labels for training.
    """
    rng = np.random.default_rng(seed)
    
    npz_path = Path(npz_path)
    json_path = Path(json_path)
    
    input_frames = []
    output_frames = []
    json_rows = []
    
    VELOCITIES = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    
    for traj_idx in range(num_trajectories):
        # Random initial physics state
        ball_x = rng.integers(1, GRID_SIZE - 1)
        ball_y = rng.integers(1, GRID_SIZE - 1)
        vel_idx = rng.integers(0, len(VELOCITIES))
        vel_x, vel_y = VELOCITIES[vel_idx]
        
        initial_physics = PhysicsState(
            ball_x=int(ball_x),
            ball_y=int(ball_y),
            vel_x=vel_x,
            vel_y=vel_y,
        )
        initial_counter = CounterState(count=0, stop=0)
        
        # Simulate trajectory using oracle
        result = simulate_chain(
            initial_physics=initial_physics,
            initial_counter=initial_counter,
            max_ticks=steps_per_trajectory,
            # Use default oracle functions
        )
        
        # Convert frames to tensors
        for i in range(len(result.frames) - 1):
            input_frame_str = result.frames_compact[i]
            output_frame_str = result.frames_compact[i + 1]
            
            input_tensor = frame_to_tensor(input_frame_str)
            output_tensor = frame_to_tensor(output_frame_str)
            
            input_frames.append(input_tensor)
            output_frames.append(output_tensor)
            
            json_rows.append({
                "trajectory": traj_idx,
                "step": i,
                "input_frame": input_frame_str,
                "output_frame": output_frame_str,
                "ball_x": result.states[i].physics_state.ball_x,
                "ball_y": result.states[i].physics_state.ball_y,
                "counter": result.states[i].counter_state.count,
                "stop": result.states[i].counter_state.stop,
            })
    
    x_data = np.asarray(input_frames, dtype=np.float32)
    y_data = np.asarray(output_frames, dtype=np.float32)
    
    # Save .npz
    np.savez(
        npz_path,
        x=x_data,
        y=y_data,
        num_trajectories=num_trajectories,
        steps_per_trajectory=steps_per_trajectory,
        grid_size=GRID_SIZE,
    )
    
    # Save JSON
    json_payload = {
        "num_trajectories": num_trajectories,
        "steps_per_trajectory": steps_per_trajectory,
        "num_samples": len(json_rows),
        "grid_size": GRID_SIZE,
        "input_shape": x_data.shape[1],
        "output_shape": y_data.shape[1],
        "transitions": json_rows[:100],  # First 100 for readability
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    
    return {"x": x_data, "y": y_data}


def exact_match_frame(predictions: torch.Tensor, targets: torch.Tensor, tolerance: float = 0.05) -> float:
    """
    Compute exact frame match accuracy.
    
    A frame matches if ALL cells are within tolerance of their targets.
    Uses the new encoding:
    - empty: 0.0
    - wall: 0.2
    - counter: 0.3 + digit*0.06 (0.30 to 0.84)
    - ball: 1.0
    """
    pred_frames = predictions.cpu().numpy()
    target_frames = targets.cpu().numpy()
    
    matches = []
    for pred, target in zip(pred_frames, target_frames):
        if np.allclose(pred, target, atol=tolerance):
            matches.append(1.0)
        else:
            matches.append(0.0)
    
    return float(np.mean(matches))


def per_cell_accuracy(predictions: torch.Tensor, targets: torch.Tensor, tolerance: float = 0.05) -> float:
    """
    Compute per-cell classification accuracy.
    
    Treats each cell as a classification problem with 4 classes:
    - empty: target < 0.15
    - wall: 0.15 <= target < 0.25
    - counter: 0.25 <= target < 0.90
    - ball: target >= 0.90
    
    A cell is correct if the prediction is within tolerance of the target.
    """
    pred_frames = predictions.cpu().numpy()
    target_frames = targets.cpu().numpy()
    
    total = 0
    correct = 0
    
    for pred, target in zip(pred_frames, target_frames):
        for p, t in zip(pred, target):
            total += 1
            if abs(p - t) <= tolerance:
                correct += 1
    
    return float(correct / total) if total > 0 else 0.0


def key_element_accuracy(predictions: torch.Tensor, targets: torch.Tensor, tolerance: float = 0.1) -> dict:
    """
    Compute accuracy for key elements: ball position and counter digit.
    
    Returns dict with individual accuracies.
    """
    from train_combined import tensor_to_frame
    
    pred_frames = predictions.cpu().numpy()
    target_frames = targets.cpu().numpy()
    
    ball_correct = 0
    ball_total = 0
    counter_correct = 0
    counter_total = 0
    
    for pred, target in zip(pred_frames, target_frames):
        pred_frame = tensor_to_frame(pred)
        target_frame = tensor_to_frame(target)
        
        # Check ball position
        pred_ball_pos = pred_frame.find('o')
        target_ball_pos = target_frame.find('o')
        
        if target_ball_pos >= 0:
            ball_total += 1
            if pred_ball_pos == target_ball_pos:
                ball_correct += 1
        
        # Check counter digit at position 0
        if len(target_frame) > 0 and target_frame[0] in '0123456789':
            counter_total += 1
            if len(pred_frame) > 0 and pred_frame[0] == target_frame[0]:
                counter_correct += 1
    
    return {
        "ball": ball_correct / ball_total if ball_total > 0 else 0.0,
        "counter": counter_correct / counter_total if counter_total > 0 else 0.0,
    }


def main() -> int:
    set_seed()

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    learning_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-4
    num_traj = int(sys.argv[4]) if len(sys.argv) > 4 else 50
    steps_per_traj = int(sys.argv[5]) if len(sys.argv) > 5 else 200

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("1) Generating combined dataset from oracle...")
    arrays = generate_combined_dataset(
        "combined_dataset.npz",
        "combined_transitions.json",
        num_trajectories=num_traj,
        steps_per_trajectory=steps_per_traj,
    )
    x_data = arrays["x"]
    y_data = arrays["y"]
    print(f"   Samples: {len(x_data)}")
    print(f"   Input shape: {x_data.shape}")
    print(f"   Output shape: {y_data.shape}")

    x_tensor = torch.tensor(x_data, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y_data, dtype=torch.float32, device=device)
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("2) Training combined model...")
    model = create_combined_model(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    metrics = {
        "epochs": [],
        "train_loss": [],
        "exact_match": [],
        "per_cell_acc": [],
        "ball_acc": [],
        "counter_acc": [],
    }

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in dataloader:
            predictions = model(batch_x)
            loss = criterion(predictions, batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            full_predictions = model(x_tensor)
            exact_acc = exact_match_frame(full_predictions, y_tensor, tolerance=0.05)
            cell_acc = per_cell_accuracy(full_predictions, y_tensor, tolerance=0.05)
            key_acc = key_element_accuracy(full_predictions, y_tensor, tolerance=0.1)

        avg_loss = total_loss / max(1, len(dataloader))
        metrics["epochs"].append(epoch)
        metrics["train_loss"].append(avg_loss)
        metrics["exact_match"].append(exact_acc)
        metrics["per_cell_acc"].append(cell_acc)
        metrics["ball_acc"].append(key_acc["ball"])
        metrics["counter_acc"].append(key_acc["counter"])

        if epoch == 1 or epoch % 10 == 0:
            print(f"   Epoch {epoch:3d}/{epochs}: loss={avg_loss:.6f}, "
                  f"exact={exact_acc*100:.1f}%, cell={cell_acc*100:.1f}%, "
                  f"ball={key_acc['ball']*100:.1f}%, counter={key_acc['counter']*100:.1f}%")

        # Early stop on high per-cell accuracy AND good key element accuracy
        if cell_acc >= 0.995 and key_acc['ball'] >= 0.95 and key_acc['counter'] >= 0.95:
            print("   Early stop: high accuracy achieved.")
            break

    print("3) Saving artifacts...")
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "input_size": 400,
        "hidden_size": 256,
        "output_size": 400,
    }
    torch.save(checkpoint, "combined_model.pth")
    Path("combined_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    final_exact = metrics["exact_match"][-1] if metrics["exact_match"] else 0.0
    final_cell = metrics["per_cell_acc"][-1] if metrics["per_cell_acc"] else 0.0
    final_ball = metrics["ball_acc"][-1] if metrics["ball_acc"] else 0.0
    final_counter = metrics["counter_acc"][-1] if metrics["counter_acc"] else 0.0
    print(f"Training complete.")
    print(f"  Final exact match: {final_exact*100:.2f}%")
    print(f"  Final per-cell accuracy: {final_cell*100:.2f}%")
    print(f"  Final ball position accuracy: {final_ball*100:.2f}%")
    print(f"  Final counter digit accuracy: {final_counter*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
