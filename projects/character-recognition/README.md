# PyTorch Character Recognition Model

A complete end-to-end AI training pipeline for character recognition using PyTorch and GitHub Actions.

## Overview

This project trains a simple neural network to recognize alphanumeric characters (A-Z, 0-9, space) from 20×20 pixel grayscale images. The training pipeline can be executed on GitHub's infrastructure using GitHub Actions.

## Features

- **Dataset Generation**: Automatically renders characters as 20×20 pixel images using PIL
- **PyTorch Model**: Simple 2-layer neural network (400 → 128 → 37 neurons)
- **GitHub Actions Workflow**: Trainable on-demand using workflow_dispatch
- **High Accuracy**: 100% validation accuracy on the training dataset
- **Model Export**: Saves trained model, metrics, and character mappings

## Project Structure

```
.
├── src/
│   ├── dataset_generator.py    # Character rendering & dataset creation
│   ├── model.py                # PyTorch network architecture
│   ├── train.py                # Training script
│   ├── inference.py            # Model validation & inference
│   ├── model.pth               # Trained model weights
│   ├── dataset.npz             # Training dataset
│   ├── metrics.json            # Training metrics
│   ├── char_map.json           # Character mappings
│   └── debug_chars/            # Rendered character images
├── .github/workflows/
│   └── train-model.yml         # GitHub Actions workflow
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

4. **Validate model**:
   ```bash
   python inference.py
   ```

### GitHub Actions Training

1. Go to **Actions** tab in your GitHub repository
2. Select **"Train Character Recognition Model"** workflow
3. Click **"Run workflow"**
4. (Optional) Configure epochs and batch size
5. View results in workflow logs
6. Download trained model from artifacts

## Dataset

- **Input**: ASCII uppercase letters (A-Z), digits (0-9), and space
- **Output**: 20×20 grayscale pixel representations (flattened to 400 features)
- **Total samples**: 37 characters
- **Font**: DejaVu Sans Mono (monospace)

## Model Architecture

```
Input (400 features: 20×20 image)
    ↓
Fully Connected Layer (128 neurons)
    ↓
ReLU Activation
    ↓
Output Layer (37 classes)
    ↓
Softmax Output
```

## Training Details

- **Optimizer**: Adam (learning rate: 0.001)
- **Loss Function**: Cross-Entropy Loss
- **Epochs**: 150 (configurable)
- **Batch Size**: 8 (configurable)
- **Device**: CPU-based (GPU support available)

## Results

- **Training Accuracy**: 100%
- **Validation Accuracy**: 100% (37/37 correct)
- **Average Confidence**: 97.61%
- **Training Time**: ~30 seconds (CPU)

### Per-Character Results

All 37 characters recognized with high confidence (76.5% - 99.9%):
- A-Z: 95.1% - 99.9% confidence
- 0-9: 95.6% - 99.5% confidence
- Space: 76.5% confidence

## Files

### Python Modules

- **dataset_generator.py**: Renders characters and creates numpy dataset
- **model.py**: Defines PyTorch network architecture
- **train.py**: Main training pipeline (dataset + training + evaluation)
- **inference.py**: Model loading and inference with validation

### Output Files

- **model.pth**: Trained model weights (~222KB)
- **dataset.npz**: Numpy arrays of image data (~59KB)
- **metrics.json**: Training loss and accuracy per epoch
- **char_map.json**: Mapping of class indices to characters
- **debug_chars/**: PNG images of each rendered character

## Dependencies

- PyTorch >= 2.0.0
- NumPy >= 1.21.0
- Pillow >= 9.0.0

## Extending the Project

### Add More Characters
Edit `src/dataset_generator.py` to include additional characters in the character set.

### Change Network Architecture
Modify `src/model.py` to use different layer sizes or add more layers.

### Customize Training Parameters
Pass different arguments to `train_model()` in `src/train.py`:
- `epochs`: Number of training iterations
- `batch_size`: Samples per batch
- `learning_rate`: Optimizer learning rate

### Enable GPU Training
The model automatically detects and uses CUDA if available:
```bash
cd src
python train.py  # Uses GPU if available, CPU otherwise
```

## GitHub Actions Workflow Configuration

The `.github/workflows/train-model.yml` workflow includes:
- **Trigger**: Manual dispatch (workflow_dispatch)
- **Environment**: Ubuntu Latest + Python 3.11
- **Configurable Parameters**:
  - `epochs`: Number of training epochs (default: 150)
  - `batch_size`: Batch size for training (default: 8)
- **Artifacts**: 
  - `trained-model` (30 days): model.pth, metrics.json, char_map.json, dataset.npz
  - `debug-characters` (7 days): Character rendering images (debug_chars/)

## Usage Notes

- The training dataset is very small (37 samples), so 100% accuracy is expected
- For production use, train on a much larger and more diverse dataset
- The model will overfit on this tiny dataset; add data augmentation and regularization for real-world use
- GitHub Actions provides free workflow minutes; check your usage limits

## Troubleshooting

### ImportError: No module named 'torch'
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### FileNotFoundError for font files
The script automatically falls back to the default font if monospace fonts are unavailable.

### Out of memory on local machine
Reduce batch size in `src/train.py` or use a machine with more RAM.

### Workflow fails on GitHub Actions
Check that:
- Python 3.11 is available
- `requirements.txt` is in the project directory
- `src/train.py` is present and executable

---

**Created**: March 2026  
**Status**: ✓ Complete and Tested  
**Accuracy**: 100% (37/37 characters)
