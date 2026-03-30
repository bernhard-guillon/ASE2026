# Character Generation (PyTorch)

Train a neural network that maps one-hot ASCII input (`0..254`) to a 20x20 grayscale glyph.

## Model

- Architecture: `255 -> 256 -> 256 -> 400`
- Activations: ReLU, ReLU, Sigmoid
- Output: flattened 20x20 image (`400` pixels in `[0,1]`)
- Loss: MSE

## Project layout

- `src/dataset_generator.py`: renders dataset from font glyphs
- `src/model.py`: network definition
- `src/train.py`: training entry point
- `src/inference.py`: validation + sample generation
- `requirements.txt`: Python dependencies

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd src
python train.py 150 8
python inference.py
```

## Produced artifacts

- `model.pth`: trained weights
- `dataset.npz`: generated dataset
- `metrics.json`: loss progression
- `char_map.json`: code-to-character mapping
- `debug_chars/`: rendered debug samples
- `pytorch_all_256_chars.npy`: full generated glyph tensor for all ASCII codes

## CI workflow

Training workflow: `.github/workflows/train-character-generation.yml`

- Trigger: push/PR/workflow_dispatch
- Artifacts: trained model bundle + debug character images

## Next stage

Export the trained model for emulator consumption:

```bash
cd ../weight-export
python3 export_generator.py
```
