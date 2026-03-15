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
