# PyTorch Character Generation Model

A complete end-to-end AI pipeline for generating 20×20 pixel character images from ASCII codes using PyTorch and GitHub Actions.

## Overview

This project trains a neural network to **generate** character images from ASCII input codes. It is the inverse of the character recognition model: given an ASCII code, the model outputs a 20×20 grayscale pixel image of that character.

## Bidirectional Pipeline

```
Character Recognition:  Image (20×20 px)  →  ASCII code
Character Generation:   ASCII code        →  Image (20×20 px)
```

## Features

- **Dataset Generation**: Automatically renders 255 ASCII characters as 20×20 pixel images using PIL
- **PyTorch Model**: 3-layer fully connected network (255 → 256 → 256 → 400 neurons)
- **GitHub Actions Workflow**: Trainable on-demand using workflow_dispatch
- **MSE Loss**: Pixel-level reconstruction loss for high-fidelity image generation
- **Model Export**: Saves trained model, metrics, character mappings, and dataset

## Project Structure

```
.
├── src/
│   ├── dataset_generator.py    # Character rendering & dataset creation
│   ├── model.py                # PyTorch network architecture
│   ├── train.py                # Training script
│   ├── inference.py            # Model validation & inference
│   ├── model.pth               # Trained model weights (after training)
│   ├── dataset.npz             # Training dataset (after training)
│   ├── metrics.json            # Training metrics (after training)
│   ├── char_map.json           # Character mappings (after training)
│   └── debug_chars/            # Rendered character images (after training)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Quick Start

### Local Training

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run training**:
   ```bash
   cd src
   python train.py
   ```

4. **Run inference**:
   ```bash
   python inference.py
   ```

### GitHub Actions Training

1. Go to the **Actions** tab in your GitHub repository
2. Select **"Train Character Generation Model"** workflow
3. Click **"Run workflow"**
4. (Optional) Configure epochs and batch size
5. View results in workflow logs
6. Download trained model from artifacts

## Dataset

- **Input**: One-hot encoded ASCII codes (0–254), 255 dimensions
- **Output**: 20×20 grayscale pixel images, flattened to 400 features (values in [0, 1])
- **Total samples**: 255 characters
- **Font**: DejaVu Sans Mono (falls back to system default)

## Model Architecture

```
Input (255 features: one-hot ASCII code)
    ↓
Fully Connected Layer (256 neurons) + ReLU
    ↓
Fully Connected Layer (256 neurons) + ReLU
    ↓
Output Layer (400 features: 20×20 pixel image)
    ↓
Sigmoid Activation (pixel values in [0, 1])
```

## Training Details

- **Optimizer**: Adam (learning rate: 0.001)
- **Loss Function**: Mean Squared Error (MSE) for pixel reconstruction
- **Epochs**: 150 (configurable)
- **Batch Size**: 8 (configurable)
- **Device**: CPU-based (GPU support available)

## GitHub Actions Workflow

The `.github/workflows/train-character-generation.yml` workflow includes:

- **Trigger**: Manual dispatch (`workflow_dispatch`)
- **Environment**: Ubuntu Latest + Python 3.11
- **Configurable Parameters**:
  - `epochs`: Number of training epochs (default: 150)
  - `batch_size`: Batch size for training (default: 8)
- **Artifacts**:
  - `trained-model` (30 days): `model.pth`, `metrics.json`, `char_map.json`, `dataset.npz`
  - `debug-characters` (7 days): Character rendering images (`debug_chars/`)

## Troubleshooting

### `ImportError: No module named 'torch'`
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `FileNotFoundError: model.pth not found`
Run training first:
```bash
cd src
python train.py
```

### Font files not found
The dataset generator automatically falls back to the PIL default font if monospace fonts are unavailable on your system.

### Workflow fails on GitHub Actions
Check that:
- Python 3.11 is available
- `requirements.txt` is in `projects/character-generation/`
- `src/train.py` is present and executable

## Extending the Project

### Change Network Architecture
Modify `src/model.py` to use different layer sizes or add more layers.

### Customize Training Parameters
Adjust arguments in `src/train.py`:
- `epochs`: Number of training iterations
- `batch_size`: Samples per batch
- `learning_rate`: Optimizer learning rate

### Enable GPU Training
The model automatically detects and uses CUDA if available:
```bash
cd src
python train.py  # Uses GPU if available, CPU otherwise
```

### Connect Both Directions
Use both models together to form an autoencoder-like pipeline:
```
ASCII code → [Generator] → 20×20 image → [Recognizer] → ASCII code
```

---

**Created**: March 2026  
**Status**: ✓ Complete  
**Pipeline**: ASCII input → 20×20 pixel character image
