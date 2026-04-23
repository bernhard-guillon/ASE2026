# Game Movement (PyTorch)

Train and validate a deterministic neural transition model for single-player movement on a `20x20` board.

This project is the first gameplay building block before squash/pong physics:

- one `#` player on a `20x20` framebuffer
- actions: `up`, `down`, `left`, `right`, `stay`
- strict boundary clamp on all borders

## Deliverables

- deterministic movement oracle (`src/movement_dataset.py`)
- exhaustive transition corpus (`20 * 20 * 5 = 2000` samples)
- PyTorch model for next-state prediction (`src/movement_model.py`, `src/train.py`)
- offline evaluator with border/action metrics (`src/evaluate.py`)
- oracle correctness tests (`src/test_oracle.py`)

## Project layout

- `src/movement_dataset.py`: oracle + dataset/corpus generation
- `src/movement_model.py`: network architecture
- `src/train.py`: training entry point
- `src/evaluate.py`: exact-match and diagnostics report
- `src/test_oracle.py`: rule/oracle unit tests

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd src
python test_oracle.py
python train.py 150 64
python evaluate.py
python export_intermediate.py
```

## Produced artifacts

- `movement_dataset.npz`: training arrays + transition labels
- `movement_transitions.json`: explicit transition table (replay-friendly)
- `movement_model.pth`: trained checkpoint
- `movement_generator.json`: emulator intermediate model (packed movement input)
- `movement_metrics.json`: training metrics
- `movement_eval.json`: evaluation summary
- `movement_mismatches.json`: failed transitions (if any)

## Emulator testing strategy

The same transition corpus is intended to be reused in emulator blackbox tests:

1. load `(state, action)` from `movement_transitions.json`
2. run emulator movement step
3. assert exact match to expected `(next_state)`

That gives one shared source of truth for training, offline validation, and runtime replay.

Replay hook in emulator test suite:

```bash
cd ../../emulator
python3 -m pytest blackbox_tests/test_game_movement_replay.py -v
```
