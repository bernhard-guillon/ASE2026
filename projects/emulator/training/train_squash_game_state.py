"""
Train game state MLP to memorize deterministic squash physics.
Exports as model JSON for emulator.

Uses softmax cross-entropy per group for training, exports with "none"
activation (raw logits). At runtime, sigmoid is applied by the merged
model's output layer, but argmax on sigmoid(logits) == argmax(logits)
since sigmoid is order-preserving.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from squash_physics import (
    INPUT_SIZE, OUTPUT_SIZE,
    BALL_X_RANGE, BALL_Y_RANGE, BALL_V_RANGE,
    PADDLE_Y_RANGE, GAME_STATE_RANGE,
    generate_all_game_state_samples,
)

# Output group boundaries (for softmax cross-entropy)
GROUPS = [
    ("ball_x", 0, BALL_X_RANGE),
    ("ball_y", BALL_X_RANGE, BALL_X_RANGE + BALL_Y_RANGE),
    ("paddle_y", BALL_X_RANGE + BALL_Y_RANGE, BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE),
    ("game_state", BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE,
                   BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE),
    ("ball_vx", BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE,
                BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE + BALL_V_RANGE),
    ("ball_vy", BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE + BALL_V_RANGE,
                OUTPUT_SIZE),
]


class GameStateMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc0 = nn.Linear(INPUT_SIZE, 64)
        self.fc1 = nn.Linear(64, 64)
        self.fc2 = nn.Linear(64, OUTPUT_SIZE)

    def forward(self, x):
        x = torch.relu(self.fc0(x))
        x = torch.relu(self.fc1(x))
        return self.fc2(x)  # logits per group


def group_ce_loss(logits, targets):
    """Cross-entropy loss per output group."""
    loss = 0.0
    for name, start, end in GROUPS:
        loss += nn.functional.cross_entropy(logits[:, start:end], targets[:, start:end].argmax(dim=1))
    return loss


def group_accuracy(logits, targets):
    """Per-group argmax accuracy."""
    correct = 0
    total = 0
    for name, start, end in GROUPS:
        pred = logits[:, start:end].argmax(dim=1)
        true = targets[:, start:end].argmax(dim=1)
        correct += (pred == true).sum().item()
        total += pred.size(0)
    return correct / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/squash_game_state.json")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.002)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Generate all training data
    print("Generating training data...")
    t0 = time.time()
    inputs_list, targets_list = [], []
    for inp, out in generate_all_game_state_samples():
        inputs_list.append(inp)
        targets_list.append(out)
    X = torch.tensor(np.array(inputs_list, dtype=np.float32), device=device)
    Y = torch.tensor(np.array(targets_list, dtype=np.float32), device=device)
    n_samples = X.shape[0]
    print(f"  {n_samples} samples in {time.time()-t0:.1f}s  X={X.shape} Y={Y.shape}")

    model = GameStateMLP().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    dataset = torch.utils.data.TensorDataset(X, Y)
    loader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    best_loss = float("inf")
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        total_acc = 0.0
        n_batches = 0
        for bx, by in loader:
            optimizer.zero_grad()
            logits = model(bx)
            loss = group_ce_loss(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            total_acc += group_accuracy(logits, by)
            n_batches += 1

        avg_loss = total_loss / n_batches
        avg_acc = total_acc / n_batches
        if avg_loss < best_loss:
            best_loss = avg_loss
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{args.epochs}  loss={avg_loss:.6f}  acc={avg_acc:.6f}")
        if avg_acc > 0.99999:
            print(f"  Converged at epoch {epoch+1}!")
            break

    # Export
    model.eval()
    state = model.state_dict()
    layers_export = []
    for name, activation in [("fc0", "relu"), ("fc1", "relu"), ("fc2", "none")]:
        w = state[f"{name}.weight"].cpu().numpy()
        b = state[f"{name}.bias"].cpu().numpy()
        in_size = w.shape[1]
        out_size = w.shape[0]
        layers_export.append({
            "name": f"squash_game_{name}",
            "input_size": in_size,
            "output_size": out_size,
            "activation": activation,
            "weights_shape": [in_size, out_size],
            "weights": w.T.tolist(),
            "biases_shape": [out_size],
            "biases": b.tolist(),
        })
    for l in layers_export:
        l["weights"] = [[float(f"{v:.10f}") for v in row] for row in l["weights"]]
        l["biases"] = [float(f"{v:.10f}") for v in l["biases"]]

    payload = {
        "metadata": {
            "model_type": "squash_game_state",
            "version": 1,
            "architecture": "56_64_64_52",
            "precision": "float32",
            "framework": "pytorch",
            "input_mapping": "squash_game_state",
            "initial_state": {
                "ball_x": 10, "ball_y": 7, "ball_vx": 1, "ball_vy": 0,
                "paddle_y": 3, "game_state": 0,
            },
        },
        "layers": layers_export,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    print(f"Exported {output_path} ({output_path.stat().st_size} bytes)")

    # Verify all samples with argmax (matching runtime behavior)
    model.eval()
    all_correct = True
    errors = 0
    for inp, expected_out in generate_all_game_state_samples():
        with torch.no_grad():
            inp_t = torch.tensor([inp], dtype=torch.float32, device=device)
            logits = model(inp_t)[0].cpu().numpy()
        match = True
        for name, start, end in GROUPS:
            if logits[start:end].argmax() != np.array(expected_out[start:end]).argmax():
                match = False
                break
        if not match:
            all_correct = False
            errors += 1
            if errors <= 3:
                for name, start, end in GROUPS:
                    pv = int(logits[start:end].argmax())
                    ev = int(np.array(expected_out[start:end]).argmax())
                    if pv != ev:
                        vals = ", ".join(f"{logits[start+i]:.3f}" for i in range(min(end - start, 10)))
                        print(f"  {name}: pred={pv} exp={ev}  vals=[{vals}]")

    if all_correct:
        print(f"  All {n_samples} samples verified: 100% argmax accuracy!")
    else:
        print(f"  WARNING: {errors}/{n_samples} argmax mismatches")
        sys.exit(1)


if __name__ == "__main__":
    main()
