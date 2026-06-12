#!/usr/bin/env python3
"""Train the router MLP for Tab-switching between sub-models.

Architecture:
  L0: 2 → 16 (ReLU)
  L1: 16 → 2 (Sigmoid)
  L2: 2 → 2 (None, identity passthrough — not trained)

Training data:
  Tab not pressed → input [1, 0] → target [1.0, 0.0] (chargen active)
  Tab pressed     → input [0, 1] → target [0.0, 1.0] (squash active)
"""

import json
import torch
import torch.nn as nn
import pathlib

SEED = 42
torch.manual_seed(SEED)

INPUT_SIZE = 2
HIDDEN_SIZE = 16
OUTPUT_SIZE = 2
NUM_EPOCHS = 5000
LR = 0.01
TARGET_LOSS = 1e-6

OUTPUT_PATH = pathlib.Path(__file__).parent / "models" / "router_tab_switch.json"


class RouterMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc0 = nn.Linear(INPUT_SIZE, HIDDEN_SIZE)
        self.fc1 = nn.Linear(HIDDEN_SIZE, OUTPUT_SIZE)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.fc0(x))
        x = self.sigmoid(self.fc1(x))
        return x


def train():
    model = RouterMLP()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()

    # Training data: Tab state one-hot → gate values
    X = torch.tensor([[1.0, 0.0],
                      [0.0, 1.0]])
    y = torch.tensor([[1.0, 0.0],
                      [0.0, 1.0]])

    model.train()
    for epoch in range(NUM_EPOCHS):
        pred = model(X)
        loss = loss_fn(pred, y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            print(f"  epoch {epoch+1:4d}  loss={loss.item():.8f}")

    if loss.item() > TARGET_LOSS:
        raise RuntimeError(f"Training did not converge: loss={loss.item():.8f} > {TARGET_LOSS}")

    print(f"Training converged: loss={loss.item():.10f}")
    return model


def export_json(model: RouterMLP):
    """Export trained weights to the model JSON format used by model_to_header."""
    model.eval()
    with torch.no_grad():
        w0 = model.fc0.weight.data.cpu().numpy()  # [16, 2]
        b0 = model.fc0.bias.data.cpu().numpy()     # [16]
        w1 = model.fc1.weight.data.cpu().numpy()   # [2, 16]
        b1 = model.fc1.bias.data.cpu().numpy()     # [2]

    # L2 identity passthrough: weights = [[1,0],[0,1]], biases = [0,0]
    w2 = [[1.0, 0.0], [0.0, 1.0]]
    b2 = [0.0, 0.0]

    def to_list(arr):
        return [[float(v) for v in row] for row in arr]

    def to_flat(arr):
        return [float(v) for v in arr]

    doc = {
        "metadata": {
            "model_type": "router_tab_switch",
            "version": 1,
            "architecture": f"{INPUT_SIZE}_{HIDDEN_SIZE}_{OUTPUT_SIZE}_{OUTPUT_SIZE}",
            "precision": "float32",
            "framework": "pytorch"
        },
        "layers": [
            {
                "name": "router_fc0",
                "input_size": INPUT_SIZE,
                "output_size": HIDDEN_SIZE,
                "activation": "relu",
                "weights_shape": [INPUT_SIZE, HIDDEN_SIZE],
                "weights": to_list(w0.T),  # transpose: model_to_header expects [input_size][output_size]
                "biases_shape": [HIDDEN_SIZE],
                "biases": to_flat(b0),
            },
            {
                "name": "router_fc1",
                "input_size": HIDDEN_SIZE,
                "output_size": OUTPUT_SIZE,
                "activation": "sigmoid",
                "weights_shape": [HIDDEN_SIZE, OUTPUT_SIZE],
                "weights": to_list(w1.T),  # transpose: [hidden_size][output_size]
                "biases_shape": [OUTPUT_SIZE],
                "biases": to_flat(b1),
            },
            {
                "name": "router_passthrough",
                "input_size": OUTPUT_SIZE,
                "output_size": OUTPUT_SIZE,
                "activation": "none",
                "weights_shape": [OUTPUT_SIZE, OUTPUT_SIZE],
                "weights": w2,
                "biases_shape": [OUTPUT_SIZE],
                "biases": b2,
            },
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(doc, f, indent=2)
    print(f"Exported router model to {OUTPUT_PATH}")


def verify():
    """Verify the exported JSON is valid and outputs are correct."""
    with open(OUTPUT_PATH) as f:
        doc = json.load(f)

    assert len(doc["layers"]) == 3, f"Expected 3 layers, got {len(doc['layers'])}"
    assert doc["layers"][0]["input_size"] == INPUT_SIZE
    assert doc["layers"][0]["output_size"] == HIDDEN_SIZE
    assert doc["layers"][1]["input_size"] == HIDDEN_SIZE
    assert doc["layers"][1]["output_size"] == OUTPUT_SIZE
    assert doc["layers"][2]["input_size"] == OUTPUT_SIZE
    assert doc["layers"][2]["output_size"] == OUTPUT_SIZE

    # Reconstruct weights and run inference
    w0 = torch.tensor(doc["layers"][0]["weights"])  # [16, 2]
    b0 = torch.tensor(doc["layers"][0]["biases"])   # [16]
    w1 = torch.tensor(doc["layers"][1]["weights"])  # [2, 16]
    b1 = torch.tensor(doc["layers"][1]["biases"])   # [2]

    # Note: JSON stores weights as [input_size][output_size]
    # Verification uses simple matmul: x @ W + b

    x_chargen = torch.tensor([1.0, 0.0])
    x_squash = torch.tensor([0.0, 1.0])

    import torch.nn.functional as F

    h0 = F.relu(x_chargen @ w0 + b0)
    o0 = torch.sigmoid(h0 @ w1 + b1)

    h1 = F.relu(x_squash @ w0 + b0)
    o1 = torch.sigmoid(h1 @ w1 + b1)

    print(f"  chargen gate: [{o0[0].item():.6f}, {o0[1].item():.6f}]")
    print(f"  squash gate:  [{o1[0].item():.6f}, {o1[1].item():.6f}]")

    assert o0[0].item() > 0.9, f"chargen gate[0] too low: {o0[0].item()}"
    assert o0[1].item() < 0.1, f"chargen gate[1] too high: {o0[1].item()}"
    assert o1[0].item() < 0.1, f"squash gate[0] too high: {o1[0].item()}"
    assert o1[1].item() > 0.9, f"squash gate[1] too low: {o1[1].item()}"

    print("Verification passed: router switches correctly")


if __name__ == "__main__":
    print("Training router MLP...")
    model = train()
    print("Exporting to JSON...")
    export_json(model)
    print("Verifying exported model...")
    verify()
    print("Done!")
