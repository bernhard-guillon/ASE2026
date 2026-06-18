# Weight Export

## Overview

Converts PyTorch model checkpoints into JSON and compact binary formats for use in the emulator pipeline.

## Usage

```bash
python3 export_generator.py
```

This reads `character_generator.json` (from the training pipeline) and produces the binary and assembly representations.

## Output Files

| File | Format | Purpose |
|---|---|---|
| `character_generator.json` | JSON | Full model weights (7.7 MB) — reference copy |
| `character_generator.bin` | Binary | Compact binary weight payload (916 KB) |
| `character_generator.json.interactive.s` | Assembly | Generated assembly from model |
| `character_generator.json.interactive.s.bin` | Binary | Assembled binary |

All output files are tracked in git as reference data.

## Key Source Files

| File | Purpose |
|---|---|
| `export_generator.py` | Main export script |
| `model_formats.py` | Model format definitions |
| `model_loader.c` | C model loader (for emulator integration) |
| `model_loader.h` | C model loader header |
| `test_model_loader.c` | Test for model loader |

## Notes

- `__pycache__/` is gitignored by root `.gitignore`
- The JSON file is used by CMake to generate `model.h` headers via `model_to_header/`
