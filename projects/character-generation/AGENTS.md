# Character Generation

## Overview

PyTorch model that generates 20x20 pixel character bitmaps from ASCII codes. Architecture: `255 -> 256 -> 256 -> 400` (input: one-hot ASCII, output: 400 pixels flattened).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `torch>=2.0.0`, `numpy>=1.21.0`, `Pillow>=9.0.0`

## Training

```bash
cd src
python train.py 150 8    # args: epochs, batch_size
```

Outputs (to `src/`):
- `model.pth` — trained checkpoint
- `dataset.npz` — training dataset
- `metrics.json` — training metrics
- `char_map.json` — character mapping

## Inference

```bash
cd src
python inference.py
```

Outputs generated character images for visual inspection.

## Key Files

| File | Purpose |
|---|---|
| `src/model.py` | MLP model definition |
| `src/train.py` | Training loop |
| `src/inference.py` | Inference + visualization |
| `src/dataset_generator.py` | Generate training dataset |
| `src/debug_chars/` | Debug character PNG outputs |

## Integration

The trained model weights are exported via `projects/weight-export/export_generator.py` to JSON + binary format for use in the emulator pipeline.

## Notes

- Outputs are generated at the project root (not `src/`), despite what `.gitignore` suggests
- The `.gitignore` rules for `src/model.pth` etc. are incorrect — outputs land at project root
