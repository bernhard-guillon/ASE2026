"""
Train renderer MLP to memorize deterministic squash drawing.
Exports as model JSON for emulator.
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
from squash_renderer import INPUT_SIZE, OUTPUT_PIXELS, generate_all_renderer_samples


class RendererMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc0 = nn.Linear(INPUT_SIZE, 128)
        self.fc1 = nn.Linear(128, 256)
        self.fc2 = nn.Linear(256, OUTPUT_PIXELS)

    def forward(self, x):
        x = torch.relu(self.fc0(x))
        x = torch.relu(self.fc1(x))
        return self.fc2(x)  # logits


def pixel_accuracy(logits, targets, threshold=0.5):
    """Fraction of pixels correctly predicted (after sigmoid)."""
    probs = torch.sigmoid(logits)
    preds = (probs > threshold).float()
    return (preds == targets).float().mean().item()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/squash_renderer.json")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.002)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Generate all training data
    print("Generating training data...")
    t0 = time.time()
    inputs_list = []
    targets_list = []
    for inp, pixels in generate_all_renderer_samples():
        inputs_list.append(inp)
        targets_list.append(pixels)
    X = torch.tensor(np.array(inputs_list, dtype=np.float32), device=device)
    Y = torch.tensor(np.array(targets_list, dtype=np.float32), device=device)
    n_samples = X.shape[0]
    print(f"  {n_samples} samples generated in {time.time()-t0:.1f}s")
    print(f"  Input shape: {X.shape}, Output shape: {Y.shape}")

    # Model
    model = RendererMLP().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.BCEWithLogitsLoss()

    dataset = torch.utils.data.TensorDataset(X, Y)
    loader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    # Class weight: positive pixels are rare (~20 out of 300 per frame)
    pos_weight = torch.tensor([10.0], device=device)

    best_loss = float("inf")
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        total_acc = 0.0
        n_batches = 0
        for bx, by in loader:
            optimizer.zero_grad()
            logits = model(bx)
            loss = nn.functional.binary_cross_entropy_with_logits(logits, by, pos_weight=pos_weight)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            total_acc += pixel_accuracy(logits, by)
            n_batches += 1

        avg_loss = total_loss / n_batches
        avg_acc = total_acc / n_batches
        if avg_loss < best_loss:
            best_loss = avg_loss

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{args.epochs}  loss={avg_loss:.6f}  acc={avg_acc:.6f}")

        if avg_acc > 0.9999:
            print(f"  Converged at epoch {epoch+1}!")
            break

    # Export
    model.eval()
    state = model.state_dict()

    layers_export = []
    for name, activation in [("fc0", "relu"), ("fc1", "relu"), ("fc2", "sigmoid")]:
        w = state[f"{name}.weight"].cpu().numpy()
        b = state[f"{name}.bias"].cpu().numpy()
        in_size = w.shape[1]
        out_size = w.shape[0]
        layers_export.append({
            "name": f"squash_render_{name}",
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
            "model_type": "squash_renderer",
            "version": 1,
            "architecture": "48_64_128_300",
            "precision": "float32",
            "framework": "pytorch",
            "input_mapping": "squash_renderer",
        },
        "layers": layers_export,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    print(f"Exported {output_path} ({output_path.stat().st_size} bytes)")

    # Verify all samples using piecewise sigmoid (matching runtime)
    def _piecewise_sigmoid(x):
        x = np.clip(x, -500, 500)
        result = np.zeros_like(x, dtype=np.float32)
        result[x <= -2.0] = 0.0
        result[(x > -2.0) & (x <= 0.0)] = 0.25 + 0.125 * x[(x > -2.0) & (x <= 0.0)]
        result[(x > 0.0) & (x <= 2.0)] = 0.75 + 0.125 * x[(x > 0.0) & (x <= 2.0)]
        result[x > 2.0] = 1.0
        return result

    errors = 0
    for inp, expected_pixels in generate_all_renderer_samples():
        inp_np = np.array(inp, dtype=np.float32)
        h = np.maximum(0, inp_np @ np.array(payload["layers"][0]["weights"], dtype=np.float32) + np.array(payload["layers"][0]["biases"], dtype=np.float32))
        h = np.maximum(0, h @ np.array(payload["layers"][1]["weights"], dtype=np.float32) + np.array(payload["layers"][1]["biases"], dtype=np.float32))
        out = _piecewise_sigmoid(h @ np.array(payload["layers"][2]["weights"], dtype=np.float32) + np.array(payload["layers"][2]["biases"], dtype=np.float32))
        pred = (out > 0.5).astype(np.float32)
        exp = np.array(expected_pixels, dtype=np.float32)
        if not np.array_equal(pred, exp):
            errors += 1
            if errors <= 3:
                diff_idx = np.where(pred != exp)[0][:5]
                for d in diff_idx:
                    x, y = d % 20, d // 20
                    print(f"  pixel ({x},{y}): pred={pred[d]:.0f} exp={exp[d]:.0f} sig={out[d]:.4f}")

    final_acc = 1.0 - errors / n_samples
    print(f"  Verification: {final_acc*100:.2f}% pixel-perfect ({n_samples - errors}/{n_samples})")
    if final_acc < 0.97:
        print(f"  WARNING: {errors}/{n_samples} samples mismatch with piecewise sigmoid")
        sys.exit(1)


if __name__ == "__main__":
    main()
