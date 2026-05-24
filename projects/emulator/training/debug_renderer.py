"""Debug renderer mismatches."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch

from squash_renderer import W, H, generate_all_renderer_samples

# Load model
model_path = Path("build/squash_renderer.json")
import json
with open(model_path) as f:
    payload = json.load(f)

class RendererMLP(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.fc0 = torch.nn.Linear(48, 128)
        self.fc1 = torch.nn.Linear(128, 256)
        self.fc2 = torch.nn.Linear(256, 300)

    def forward(self, x):
        x = torch.relu(self.fc0(x))
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

model = RendererMLP()
state = {}
for name in ["fc0", "fc1", "fc2"]:
    w = np.array(payload["layers"][{"fc0": 0, "fc1": 1, "fc2": 2}[name]]["weights"], dtype=np.float32).T
    b = np.array(payload["layers"][{"fc0": 0, "fc1": 1, "fc2": 2}[name]]["biases"], dtype=np.float32)
    state[f"{name}.weight"] = torch.from_numpy(w)
    state[f"{name}.bias"] = torch.from_numpy(b)
model.load_state_dict(state)
model.eval()

device = torch.device("cpu")

# Find all mismatches and categorize
errors_by_gs = {0: 0, 1: 0}
errors_by_location = {}

for inp, expected_pixels in generate_all_renderer_samples():
    gs = int(np.argmax(inp[46:48]))
    with torch.no_grad():
        inp_t = torch.tensor([inp], dtype=torch.float32, device=device)
        logits = model(inp_t)
        probs = torch.sigmoid(logits[0]).cpu().numpy()
        pred = (probs > 0.5).astype(np.float32)
    exp = np.array(expected_pixels, dtype=np.float32)
    if not np.array_equal(pred, exp):
        errors_by_gs[gs] += 1
        diff_indices = np.where(pred != exp)[0]
        for di in diff_indices:
            x, y = di % W, di // W
            key = (x, y, gs)
            errors_by_location[key] = errors_by_location.get(key, 0) + 1

print(f"Mismatches: live={errors_by_gs[0]}, game_over={errors_by_gs[1]}")
print(f"Unique error locations: {len(errors_by_location)}")
# Top 10 error locations
sorted_locations = sorted(errors_by_location.items(), key=lambda x: -x[1])
for (x, y, gs), count in sorted_locations[:15]:
    print(f"  pixel=({x},{y}) gs={gs}  count={count}")
