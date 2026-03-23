# Neural Character Generation Test Summary

**Date**: 2026-03-23  
**Test Suite**: All 256 ASCII characters (0-255)  
**Threshold**: 80% pixel match with PyTorch reference  

## Executive Summary

❌ **All 256 tests FAILED** (0.0% pass rate)
- Average match: **~53%** (far below 80% threshold)
- Best case: 56.8% (character 'w')
- Worst case: 50.2% (characters 209, 219)

**Root Cause**: RISC-V neural over-saturation issue
- RISC-V neural outputs ~190 pixels/character
- PyTorch reference outputs ~28 pixels/character
- Massive pixel mismatch causes low similarity

---

## Test Setup

### Phase 1: PyTorch Reference Generation ✅
- Generated all 256 characters from PyTorch model
- Model architecture: 255→256→256→400 (3 layers, ReLU+Sigmoid)
- Output format: # and space (20×20 grid)
- Files:
  - `pytorch_all_256_chars.npy` - Binary arrays
  - `pytorch_256_metadata.json` - Character metadata
  - `pytorch_256_framebuffers.txt` - ASCII art format

### Phase 2: Emulator Enhancement ✅
- Emulator already supports required flags:
  - `--char X` - Set character input
  - `--cycles N` - Set execution cycle limit
  - `--render-framebuffer` - Output 20×20 grid as ASCII
- No modifications needed

### Phase 3: Blackbox Test Suite ✅
- Created `test_neural_256_chars.py`
- Tests neural.elf against PyTorch for all 256 chars
- Extracts framebuffer output and compares pixel-by-pixel
- Pass criterion: ≥80% pixel match

---

## Test Results

### Overall Statistics

| Metric | Value |
|--------|-------|
| **Total Characters Tested** | 256 |
| **Tests Passed** | 0 |
| **Tests Failed** | 256 |
| **Pass Rate** | 0.0% |
| **Average Match** | ~53% |
| **Best Match** | 56.8% (char 119 'w') |
| **Worst Match** | 50.2% (chars 209, 219) |

### Match Distribution

| Match Range | Count | Percentage |
|-------------|-------|------------|
| 50-51% | 30 | 11.7% |
| 51-52% | 45 | 17.6% |
| 52-53% | 80 | 31.3% |
| 53-54% | 60 | 23.4% |
| 54-55% | 30 | 11.7% |
| 55-56% | 8 | 3.1% |
| 56-57% | 3 | 1.2% |

**Pattern**: All characters cluster around 50-56% match (essentially random)

### Character Type Breakdown

| Type | Characters | Avg Match | Best | Worst |
|------|------------|-----------|------|-------|
| Control (0-31) | 32 | 52.5% | 56.5% | 51.2% |
| Printable (32-126) | 95 | 53.8% | 56.8% | 51.5% |
| Extended (127-255) | 129 | 53.5% | 55.8% | 50.2% |

**Observation**: No significant difference between character types

---

## Root Cause Analysis

### Problem: Over-Saturation

The RISC-V neural network implementation produces heavily over-saturated outputs:

```
PyTorch Expected:        RISC-V Neural Actual:
     ##                  # # #  #  ### #   
    ###                 ##   ##      #####  
    # ##                # #         # # # # 
    #  #                ####### ######      
   ##  #                ##     # ## ##  ##  
   #   ##                ## ##  ## # #      
   #   ##                     #   ## #   #  #
  #######               ##  # # ####  ###  #
  ##    ##               #  # #  ###        
 ##     ##              #   # # # ##        
 ##      ##               # # # # ## #     #
(~28 pixels)            (~190 pixels - way too many!)
```

### Technical Analysis

1. **Output Layer Saturation**
   - Sigmoid activation producing values near 1.0 for most pixels
   - Should produce sparse outputs (few pixels ON)
   - Actually produces dense outputs (most pixels ON)

2. **Weight/Bias Scaling Issue**
   - Weights may be incorrectly scaled during RISC-V conversion
   - Biases may push activations into saturation region
   - Fixed-point arithmetic may introduce errors

3. **Activation Function Implementation**
   - Sigmoid approximation may be inaccurate
   - Could be producing values that are too high
   - Threshold at 0.5 captures too many pixels

---

## Detailed Examples

### Example 1: Character 'A' (ASCII 65)

**Match**: 56.0%

```
PyTorch Reference:       RISC-V Neural Output:
     ##                  # # #  #  ### #   
    ###                 ##   ##      #####  
    # ##                # #         # # # # 
    #  #                ####### ######      
   ##  #                ##     # ## ##  ##  
   #   ##                ## ##  ## # #      
   #   ##                     #   ## #   #  #
  #######               ##  # # ####  ###  #
  ##    ##               #  # #  ###        
 ##     ##              #   # # # ##        
 ##      ##               # # # # ## #     #
```

**Issue**: Neural output has ~4x more pixels than expected

### Example 2: Character 'w' (ASCII 119) - Best Match

**Match**: 56.8%

Still far below 80% threshold despite being the "best" result.

### Example 3: Character 209 - Worst Match

**Match**: 50.2%

Essentially random - no correlation with PyTorch reference.

---

## Next Steps (Phase 6)

### Immediate Actions

1. **Debug RISC-V Activation Functions**
   - Check sigmoid implementation accuracy
   - Verify output is in [0, 1] range
   - Test with known inputs

2. **Verify Weight/Bias Conversion**
   - Compare PyTorch weights with RISC-V embedded weights
   - Check fixed-point scaling factors
   - Validate conversion script

3. **Test Output Layer Separately**
   - Run just the final layer with known inputs
   - Check if saturation happens in FC3 or earlier
   - Isolate the problematic layer

4. **Adjust Threshold or Scaling**
   - If output values are consistently high, adjust threshold
   - Or scale weights down to prevent saturation
   - Or add normalization layer

### Success Criteria

- Target: ≥80% pixel match with PyTorch
- Stretch: ≥90% pixel match
- Minimum: ≥70% pixel match for pass

### Expected Outcome

After fixing over-saturation:
- Pixel counts: ~190 → ~28 (match PyTorch)
- Match percentage: ~53% → ~85% (acceptable range)
- Pass rate: 0% → 90%+ (most characters pass)

---

## Conclusion

✅ **Test Infrastructure Complete**
- PyTorch reference data: ✅ Generated
- Emulator integration: ✅ Working
- Test suite: ✅ Implemented
- Automated testing: ✅ Functional

❌ **RISC-V Neural Implementation Broken**
- Over-saturation issue confirmed
- 0/256 characters pass validation
- Requires debugging before production use

**Priority**: Fix Phase 6 (RISC-V neural debugging) before proceeding

---

**Test Files**:
- `test_neural_256_chars.py` - Main test suite
- `pytorch_all_256_chars.npy` - PyTorch reference
- `neural.elf` - RISC-V neural executable (broken)

**Status**: BLOCKED on Phase 6 debugging
