# PyTorch Character Generation Model Output

## Overview

This directory contains the PyTorch character generation model and its output.

## Generated Character Maps

### 1. **PYTORCH_CHARACTER_MAP.md** (45.6 KB)
Complete visual reference for all 95 printable ASCII characters (32-126).
- 20×20 pixel grids (█ for ON, space for OFF)
- Pixel counts and percentages
- ASCII codes and character representations
- **Purpose**: Visual review and documentation

### 2. **PYTORCH_MODEL_REVIEW.md** (6.5 KB)
Comprehensive analysis and summary of the PyTorch model output.
- Statistical breakdown by category
- Quality assessment and examples
- Comparison with static and RISC-V implementations
- Recommendations for Phase 6
- **Purpose**: Technical analysis and planning

### 3. **generated_chars.npz**
Binary numpy archive with pixel arrays for all 95 characters.
- Format: 95 arrays of shape (400,) as float32
- Values in [0.0, 1.0] range
- **Purpose**: Data processing and analysis

### 4. **generated_chars.json**
Lightweight JSON metadata for all characters.
- ASCII code, character representation, pixel count
- **Purpose**: Quick reference and scripting

## Key Statistics

| Metric | Value |
|--------|-------|
| Characters Generated | 95 (ASCII 32-126) |
| Average Pixels ON | 27.9/400 (7.0%) |
| Min Pixels | 0 (space, period, etc.) |
| Max Pixels | 51 (@ symbol) |
| Uppercase Average | 37.4 pixels |
| Lowercase Average | 30.5 pixels |
| Numbers Average | 31.5 pixels |

## Model Assessment

✅ **Quality**: Excellent
- Balanced pixel distribution
- Recognizable characters
- No over/under-saturation
- Appropriate visual variation

✅ **Suitability**: Reference implementation
- Use as ground truth for RISC-V implementation
- Validate neural network compilation
- Benchmark output quality

## Comparison with Other Models

| Model | Avg Pixels | Status | Notes |
|-------|-----------|--------|-------|
| PyTorch | 27.9 | ✅ Reference | Good distribution |
| Static Lookup | 29.2 | ✅ Perfect | Exact font match |
| RISC-V Compiled | ~190 | ❌ Broken | Over-saturated |

## Phase 6 Action Items

1. **Debug RISC-V Neural** - Fix output over-saturation
2. **Validate Against PyTorch** - Create comparison test suite
3. **Optimize Performance** - Implement bit-shifting
4. **Extend Resolution** - Move to 100×100 framebuffer
5. **Retrain Model** - Improve accuracy if needed

## File Locations

- **Model**: `model.pth`
- **Character Map**: `PYTORCH_CHARACTER_MAP.md`
- **Review**: `PYTORCH_MODEL_REVIEW.md`
- **Binary Data**: `generated_chars.npz`
- **Metadata**: `generated_chars.json`

---

**Generated**: 2026-03-22  
**Status**: ✅ Complete and ready for review
