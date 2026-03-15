# ASE2026
Advanced Systems Engineering 2026

## Projects

### 1. PyTorch Character Recognition Model
**Status**: ✓ Complete  
**Accuracy**: 100% (37/37 characters)

A complete end-to-end AI training pipeline for character recognition using PyTorch and GitHub Actions. Trains a neural network to recognize alphanumeric characters (A-Z, 0-9, space) from 20×20 pixel grayscale images.

**Key Features**:
- Automatic dataset generation using PIL/Pillow
- Simple 2-layer PyTorch neural network (400 → 128 → 37 neurons)
- GitHub Actions workflow for on-demand training (manual dispatch)
- 100% validation accuracy on training set
- Comprehensive model export (weights, metrics, character mappings)

**Quick Start**:
```bash
cd projects/character-recognition
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
python train.py          # Generate dataset & train model
python inference.py      # Validate model performance
```

**GitHub Actions**: Trigger training manually via **Actions** → **Train Character Recognition Model** → **Run workflow**

📖 [Full Documentation](./projects/character-recognition/README.md)

---

### 2. PyTorch Character Generation Model
**Status**: ✓ Complete

A complete end-to-end AI pipeline for generating 20×20 pixel character images from ASCII codes using PyTorch and GitHub Actions. The inverse of the character recognition model: given an ASCII code, the model outputs a 20×20 grayscale pixel image.

**Key Features**:
- Automatic dataset generation using PIL/Pillow
- 3-layer PyTorch neural network (255 → 256 → 256 → 400 neurons)
- GitHub Actions workflow for on-demand training (manual dispatch)
- MSE loss for pixel-level reconstruction
- Comprehensive model export (weights, metrics, character mappings)

**Quick Start**:
```bash
cd projects/character-generation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
python train.py          # Generate dataset & train model
python inference.py      # Validate model performance
```

**GitHub Actions**: Trigger training manually via **Actions** → **Train Character Generation Model** → **Run workflow**

> **Note**: The canonical GitHub Actions workflow is `.github/workflows/train-character-generation.yml` in the repository root. GitHub Actions only picks up workflows from the root `.github/workflows/` directory. The file at `projects/character-generation/.github/workflows/train-model.yml` is a non-functional reference copy — it will **not** be executed by GitHub Actions and must be kept in sync with the root workflow manually.

📖 [Full Documentation](./projects/character-generation/README.md)
