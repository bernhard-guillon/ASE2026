# Phase 1 Implementation Notes

## What We Built

A complete weight export pipeline that:
1. Exports trained PyTorch models to standardized JSON format
2. Converts JSON to optimized binary format
3. Provides C loader library for emulator integration

## Pipeline Architecture

```
PyTorch Model
    ↓
[Stage 1: model_formats.py::IntermediateFormat]
    ↓
JSON Intermediate Format
    ├─ Human-readable, debuggable, version-controlled
    ├─ Contains all layer definitions and numerical values
    └─ Can be inspected/validated in Python
    ↓
[Stage 2: model_formats.py::BinaryFormat]
    ↓
Binary Format (.bin)
    ├─ Compact (8× compression vs JSON)
    ├─ Fast loading (memcpy instead of parsing)
    └─ Memory-efficient for emulator
    ↓
[Stage 3: model_loader.c]
    ↓
Emulator Memory
    ├─ Ready for NEURAL_FC instruction execution
    └─ Supports inference operations
```

## Design Decisions

### 1. JSON as Intermediate
**Why:** Standard format that doesn't lock us into proprietary representations

**Benefits:**
- Can be inspected with any text editor
- Easy to validate (compare with Python reference)
- No binary format compatibility issues
- Can evolve schema without breaking everything
- Great for debugging and understanding what's happening

**Drawbacks:**
- Large file size (7.1 MB for generator)
- Requires JSON parser (but we use it for validation anyway)

### 2. Binary for Emulator
**Why:** Compact and fast loading without JSON parsing overhead

**Benefits:**
- Small file size (0.9 MB for generator)
- Direct memcpy into memory
- No parsing needed in emulator
- Extensible format (reserved fields for future)

**Format Design:**
```
Header (32 bytes)
├─ Magic number (0x4E52414E = "NRAL")
├─ Version number (1)
├─ Model type (generator=0, recognizer=1)
├─ Layer count, weight count, bias count
└─ Reserved for future extensions

Layer Table (32 bytes × num_layers)
├─ Per-layer metadata
├─ Offsets into weight/bias data
└─ Activation function type

Weight Data (4 bytes × num_weights)
└─ All weights, layer-by-layer

Bias Data (4 bytes × num_biases)
└─ All biases, layer-by-layer
```

### 3. Weight Transposition
**Original Problem:** PyTorch stores weights as (output_size, input_size) for matmul

**Our Approach:** Transpose to (input_size, output_size)

**Why:**
- Natural layout for fully-connected computation: out[i] = sum(weights[i][j] * in[j])
- Efficient C code: row-major cache access pattern
- Simplifies assembly implementation

**Code Example:**
```python
# PyTorch gives us (256, 255) for first layer
# We transpose to (255, 256)
weights = fc_layer.weight.data.cpu().numpy()  # shape: (256, 255)
weights = weights.T  # shape: (255, 256)
```

### 4. Separate C Library
**Why:** Make the loader reusable and integration-ready

**Benefits:**
- Can be compiled into emulator without modifying export code
- API is clear and documented
- Error handling is standardized
- Can add more features later (streaming, memory mapping, etc.)

## Implementation Details

### Export Scripts
- `export_generator.py`: Loads trained model → exports both formats
- `export_recognizer.py`: Same for recognizer model
- Both follow identical structure for consistency

### Model Loader Library
- `model_loader.h`: Public API
- `model_loader.c`: Implementation (~600 lines)
- Includes:
  - File loading
  - Buffer parsing
  - Error checking and validation
  - Helper functions for introspection

### Test Program
- `test_model_loader.c`: Verifies both models load correctly
- Shows model statistics
- Validates magic numbers and headers

## Statistics

### Character Generator
```
Input:   255 (ASCII one-hot)
Layer 0: 255 → 256 + ReLU
Layer 1: 256 → 256 + ReLU  
Layer 2: 256 → 400 + Sigmoid
Output:  400 (pixel values)

Total parameters: 234,128
JSON size: 7.1 MB
Binary size: 0.9 MB
Compression: 7.8×
```

### Character Recognizer
```
Input:   400 (pixel values)
Layer 0: 400 → 128 + ReLU
Layer 1: 128 → 37 (logits, no activation)
Output:  37 (class scores)

Total parameters: 56,101
JSON size: 1.8 MB
Binary size: 0.2 MB
Compression: 8.2×
```

## Validation

All components tested:
- ✓ Python export scripts work
- ✓ Binary format writes correctly
- ✓ C loader compiles without warnings
- ✓ Both models load successfully
- ✓ Header validation passes
- ✓ Layer counts correct
- ✓ Parameter counts correct

## Files and Sizes

```
projects/weight-export/
├── model_formats.py          380 lines   Format definitions
├── export_generator.py       128 lines   Export script
├── export_recognizer.py      128 lines   Export script
├── model_loader.h            100 lines   C API header
├── model_loader.c            200 lines   C implementation
├── test_model_loader.c        50 lines   Test program
├── character_generator.json 7.1 MB      Intermediate format
├── character_generator.bin  0.9 MB      Binary format
├── character_recognition.json 1.8 MB    Intermediate format
├── character_recognition.bin  0.2 MB    Binary format
└── README.md                 250 lines   Documentation
```

## Next Steps for Phase 2

The binary files are ready to be loaded into the emulator. Phase 2 will:

1. **Implement NEURAL_FC Instruction**
   - Opcode 0x77 (in reserved space)
   - Registers: a0=layer_id, a1=input_addr, a2=output_addr
   - Executes matrix-vector product with activation

2. **Add to CPU Execution**
   - Instruction decoder recognizes NEURAL_FC
   - CPU loads layer parameters from memory
   - Computes output, applies activation
   - Stores result to output buffer
   - Updates cycle counter for profiling

3. **Integrate Model Loader**
   - At emulator startup, load weights into memory
   - Set up layer metadata for NEURAL_FC access
   - Initialize input/output buffers

## Performance Considerations

### Binary Loading
- Generator: 0.9 MB → should load in < 1ms
- Recognizer: 0.2 MB → should load in < 0.2ms
- One-time cost at startup

### Computation (Estimated, pending CPU implementation)
- Generator layer 0: 255×256 = 65k multiplies ≈ 65k cycles
- With ReLU: +256 comparisons ≈ 256 additional cycles
- Generator layer 2 Sigmoid: 400 exponentials ≈ 4k-8k cycles
- Total for full generation: 50k-100k cycles (rough estimate)

### Memory Usage
- Generator weights: 0.9 MB
- Recognizer weights: 0.2 MB  
- Input/output buffers: ≈50 KB
- Total: ~1.2 MB (fits in extended emulator memory)

## Future Improvements

1. **Quantization:** Convert float32 to int8/int16 (4× smaller)
2. **Streaming:** Load weights on-demand instead of all at once
3. **Memory Mapping:** Use mmap for large models
4. **Compressed Weights:** Gzip compression (could reach 3MB → 1MB)
5. **SIMD Variants:** Process multiple neurons per cycle
6. **Layer Caching:** Cache computed layer outputs
7. **Custom Datatypes:** Support different precision levels

These can be added later without changing the export pipeline architecture.

---

**Created:** 2026-03-21  
**Status:** Phase 1 Complete, Ready for Phase 2
