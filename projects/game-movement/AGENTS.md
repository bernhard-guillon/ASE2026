# Game Movement

## Overview

Deterministic 20x20 grid player-movement model. Given a state (player position) and action (up/down/left/stay), predicts the next state. Used for closed-loop neural game behavior.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `torch>=2.0.0`, `numpy>=1.21.0`

## Training

```bash
cd src
python train.py
```

Outputs (to `src/`):
- `movement_model.pth` — trained checkpoint
- `movement_generator.json` — exported model weights
- `movement_transitions.json` — deterministic transition table

## Key Files

| File | Purpose |
|---|---|
| `src/movement_model.py` | Model architecture |
| `src/movement_dataset.py` | Dataset definition |
| `src/train.py` | Training script |
| `src/evaluate.py` | Evaluation metrics |
| `src/export_counter_char_combined.py` | Combined model export |

## Tests

```bash
cd src
python -m pytest test_oracle.py -v
```

## Notes

- The `prototype/` directory is empty (stale)
- Generated `.json` and `.pth` files are tracked in git as reference data
- `.venv/` lives at `src/.venv/` (not ideal — should be at project root)
