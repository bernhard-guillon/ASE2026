# Weight Export Pipeline

Three-stage pipeline for exporting PyTorch neural network models for use in the RISC-V emulator.

## Pipeline Overview

```
PyTorch Model (.pth)
    ↓
    ├─→ Stage 1: PyTorch → Intermediate Format (JSON)
    │   • Human-readable
    │   • Debuggable
    │   • Portable
    │
    ├─→ Stage 2: JSON → Binary Format (.bin)
    │   • Compact
    │   • Fast C loading
    │   • Memory-efficient
    │
    └─→ Stage 3: Binary → Emulator Memory
        • Load at startup
        • Ready for NEURAL_FC execution
```

## Generated Files

### character_generator.json (7.4 MB)
Intermediate format for character generation model:
- **Input:** 255-dimensional one-hot ASCII vector
- **Output:** 400 pixel values (20×20 glyph)
- **Layers:**
  - Layer 0: 255→256 + ReLU
  - Layer 1: 256→256 + ReLU
  - Layer 2: 256→400 + Sigmoid
- **Total Parameters:** 234,128
- **Use Case:** Debugging, validation, reference implementation

### character_generator.bin (0.9 MB)
Binary format for fast C loading:
- Header + layer table + weights + biases
- Ready to load into emulator memory
- Minimal overhead

### Legacy recognizer artifacts
Historical recognizer files and scripts may still exist in this directory for traceability,
but they are outside the current ASE2026 project scope and are not used in the final build/validation path.

## JSON Intermediate Format Specification

### Structure

```json
{
  "metadata": {
    "model_type": "generator" | "recognizer",
    "version": 1,
    "architecture": "fully-connected",
    "precision": "float32",
    "framework": "pytorch"
  },
  "layers": [
    {
      "name": "layer_0",
      "input_size": 255,
      "output_size": 256,
      "activation": "relu" | "sigmoid" | "none",
      "weights_shape": [255, 256],
      "weights": [[w00, w01, ...], [w10, w11, ...], ...],
      "biases_shape": [256],
      "biases": [b0, b1, ..., b255]
    },
    ...
  ]
}
```

### Benefits
- **Human-readable:** Can be inspected with any text editor or Python
- **Debuggable:** Easy to verify layer shapes and values
- **Portable:** No binary format differences across architectures
- **Validatable:** Load in Python, run inference, compare with original model
- **Version-controlled:** Can track changes to models over time

## Binary Format Specification

### File Layout
```
Header (32 bytes):
  - magic: 0x4E52414E ("NRAL")
  - version: 1
  - model_type: 0=generator, 1=recognizer
  - num_layers: number of layers
  - total_weight_floats: total weights count
  - total_bias_floats: total biases count
  - reserved: 4 bytes

Layer Table (32 bytes per layer):
  For each layer:
  - input_size: uint32
  - output_size: uint32
  - activation: uint32 (0=relu, 1=sigmoid, 2=none)
  - weight_offset: uint32 (byte offset in weight data)
  - bias_offset: uint32 (byte offset in bias data)
  - reserved: 12 bytes

Weight Data (4 bytes per float32):
  All weights packed sequentially
  Layer 0 weights, Layer 1 weights, ...

Bias Data (4 bytes per float32):
  All biases packed sequentially
  Layer 0 biases, Layer 1 biases, ...
```

### Benefits
- **Compact:** Minimal overhead, just raw float32 data
- **Fast:** Direct memory load, no parsing needed
- **Efficient:** Linear memory access pattern

## Usage

### Export Models

```bash
cd projects/weight-export

# Export character generator
python3 export_generator.py

# Optional: export legacy recognizer model (not part of current project scope)
python3 export_recognizer.py
```

This creates:
- `character_generator.json` + `.bin`
- (optional legacy) recognizer JSON + `.bin`

### Loading in Python (Verification)

```python
import json

with open('character_generator.json') as f:
    model = json.load(f)

for layer in model['layers']:
    print(f"Layer: {layer['input_size']}→{layer['output_size']}")
    weights = layer['weights']  # Python nested lists
    biases = layer['biases']
    # Validate, visualize, etc.
```

### Loading in C (Emulator)

The binary format can be loaded using a simple C parser:

```c
#include <stdint.h>
#include <stdio.h>

typedef struct {
    uint32_t input_size;
    uint32_t output_size;
    uint32_t activation;  // 0=relu, 1=sigmoid, 2=none
    uint32_t weight_offset;
    uint32_t bias_offset;
    uint32_t reserved[3];
} LayerEntry;

typedef struct {
    uint32_t magic;           // 0x4E52414E
    uint32_t version;         // 1
    uint32_t model_type;      // 0=gen, 1=recog
    uint32_t num_layers;
    uint32_t total_weights;
    uint32_t total_biases;
    uint8_t reserved[4];
} ModelHeader;

// Load model
FILE *f = fopen("character_generator.bin", "rb");
ModelHeader header;
fread(&header, sizeof(header), 1, f);

LayerEntry layers[header.num_layers];
fread(layers, sizeof(LayerEntry), header.num_layers, f);

float weights[header.total_weights];
fread(weights, sizeof(float), header.total_weights, f);

float biases[header.total_biases];
fread(biases, sizeof(float), header.total_biases, f);

fclose(f);
```

## Implementation Details

### Weight Ordering
- PyTorch stores weights as (output_size, input_size)
- Pipeline transposes to (input_size, output_size)
- C code expects (input_size, output_size) for efficient row-wise access

### Activation Functions
- `relu`: max(0, x)
- `sigmoid`: 1 / (1 + exp(-x))
- `none`: x (identity)

### Precision
- All weights and biases stored as IEEE 754 float32
- Sufficient for these small models
- Can be extended to int8/fp16 for optimization

## Emulator Memory Map

When models are loaded into the RISC-V emulator at startup:

```
0x00000000 - 0x00003FFF: Program Code (16 KB)
0x00004000 - 0x00007FFF: Stack (16 KB)
0x00008000 - 0x0000FFFF: Heap (32 KB)
0x00010000 - 0x000F56FF: Character Generator Weights (936 KB)
               ├─ 0x00010000: Header (32 bytes)
               │  └─ Magic: 0x4E52414E, Version: 1, Type: 0
               ├─ 0x00010020: Layer Table (96 bytes)
               │  └─ 3 layers × 32 bytes each
               ├─ 0x00010080: Weight Data (932,864 bytes)
               │  └─ Layer 0-2 weights, sequential
               └─ 0x000F3C80: Bias Data (3,648 bytes)
                  └─ Layer 0-2 biases, sequential

0x000F4ABC - 0x0012B6FB: Reserved legacy model region (currently unused)

0x00200000 - 0x003FFFFF: I/O and Framebuffer (2 MB)
               ├─ Framebuffer syscall operations
               └─ Character glyph output

0x04000000 - 0xFFFFFFFF: Available for mmap (3 GB+)
               └─ Dynamic allocation via mmap2 syscall
```

### Memory Access Patterns for NEURAL_FC

**Layer Metadata Access:**
```c
// Base addresses
#define GENERATOR_BASE    0x10000
#define LEGACY_BASE       0xF4ABC

// Calculate layer entry offset
uint32_t layer_base = (model_type == GENERATOR) ? GENERATOR_BASE : LEGACY_BASE;
uint32_t layer_offset = layer_base + 32 + (layer_id * 32);

// Read layer parameters
uint32_t input_size  = memory.read32(layer_offset + 0);
uint32_t output_size = memory.read32(layer_offset + 4);
uint32_t activation  = memory.read32(layer_offset + 8);
uint32_t weight_off  = memory.read32(layer_offset + 12);
uint32_t bias_off    = memory.read32(layer_offset + 16);
```

**Weight Access:**
```c
// Weight data starts after layer table
uint32_t weights_start = layer_base + 32 + (num_layers * 32);
uint32_t weight_ptr = weights_start + weight_off;

// Read weight at position [i][j]
float weight = memory.readFloat(weight_ptr + (i * output_size + j) * 4);
```

**Bias Access:**
```c
// Biases follow weights
uint32_t biases_start = weights_start + (total_weights * 4);
uint32_t bias_ptr = biases_start + bias_off;

// Read bias at position [j]
float bias = memory.readFloat(bias_ptr + j * 4);
```

### Memory Efficiency

| Component | Size | % of Emulator |
|-----------|------|---------------|
| Generator model | 936 KB | 0.36% |
| Reserved legacy region | 224 KB | 0.09% |
| **Generator + reserved region** | **1.1 MB** | **0.43%** |
| Available (256 MB) | **254.9 MB** | **99.57%** |

## Next Steps

1. **Phase 2:** Implement NEURAL_FC instruction in CPU
   - Add opcode decoder for 0x77
   - Implement matrix-vector product
   - Add ReLU and Sigmoid activation functions
   
2. **Phase 3:** Test inference against Python reference
   - Load models at emulator startup
   - Execute sample NEURAL_FC instructions
   - Compare outputs with trained model
   
3. **Phase 4:** Integrate with framebuffer for visualization
   - Add framebuffer syscall (opcode 999)
   - Render generated glyphs to output
   - Create demonstration program

## Files

- `model_formats.py` - Format definitions and converters
- `export_generator.py` - Export character generator
- `export_recognizer.py` - Export legacy recognizer (optional, out of scope)
- `character_generator.json` - Generator intermediate format
- `character_generator.bin` - Generator binary format
- `character_recognition.json` - Legacy recognizer intermediate format
- `character_recognition.bin` - Legacy recognizer binary format

## Statistics

### Character Generator
- Total size: 936,640 bytes (0.9 MB)
- Weights: 932,864 bytes
- Biases: 3,648 bytes
- Density: 4 bytes per parameter (float32)

### Legacy Recognizer (optional)
- Total size: 224,500 bytes (0.2 MB)
- Weights: 223,744 bytes
- Biases: 660 bytes
- Density: 4 bytes per parameter (float32)

### Combined
- Total: ~1.1 MB including reserved legacy region
- Fits comfortably in 256 KB extended emulator memory + external storage
- Can be loaded at startup or streamed on demand
