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

# Or via CTest targets:
cd build
ctest -R game_movement --output-on-failure
```

Build-ready movement ELF (easy target):

```bash
cd ../../emulator
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target movement_elf -j4
```

Output: `projects/emulator/build/movement.elf`

## Squash model training (`j/k` paddle control)

This extends from movement-only into game-frame prediction:

- Input: current `20x20` framebuffer (`400`) + key one-hot (`255`, ASCII channel)
- Keys: `j` = up, `k` = down, `space` = stay
- Output: next `20x20` framebuffer (`400`)

Run from `src/`:

```bash
cd src
python3 test_squash_oracle.py
python3 train_squash.py 60 128 0.001 600 120
python3 evaluate_squash.py
```

Produced artifacts:

- `squash_dataset.npz`
- `squash_transitions.json`
- `squash_model.pth`
- `squash_metrics.json`
- `squash_eval.json`
- `squash_mismatches.json`

Build ELF from squash model for emulator runs:

```bash
cd ../../emulator
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target game_movement_elf -j4
```

Output: `projects/emulator/build/game-movement.elf`

Run on C++ emulator (example with `j` = up):

```bash
cd ../../emulator
./build/emulator_runner ./build/game-movement.elf --char-code 106 --cycles 12000000 --render-framebuffer --dump-framebuffer
```

Note: the squash model is larger than the movement-only model, so use a higher cycle budget (`>= 10,000,000`) for visible framebuffer output.

Key codes:

- `j` (up): `106`
- `k` (down): `107`
- `space` (stay): `32`

## Throwaway terminal squash prototype

Prototype path: `projects/game-movement/prototype/terminal_squash.py`

```bash
cd prototype
python3 terminal_squash.py
```

Controls:

- `up/down` arrows (or `w/s`): move paddle by one cell per tick
- `p`: write ASCII screenshot to `prototype/screenshots/`
- `r`: reset game
- `space`: pause/resume
- `q`: quit

Quick non-interactive check:

```bash
cd prototype
python3 test_squash_logic.py
python3 terminal_squash.py --headless-ticks 80 --script "ddddddssssssuuuuuu" --seed 7
```
