# Neural Network Execution on RISC-V Emulator

## Overview

This guide explains how trained neural network models are compiled into executable RISC-V code and run on the emulator.

## Architecture

### Three-Phase Pipeline

```
JSON Model
    ↓
[Phase 1] Code Generation (model_compiler.py)
    • Binary format encoding (28B header + layer table + weights/biases)
    • Assembly generation (input mapping, layer computation, output mapping)
    ↓
[Phase 2] Assembly & Linking
    • riscv64-elf-as: Assemble to object file
    • riscv64-elf-ld: Link to 32-bit ELF with position-independent code
    ↓
[Phase 3] Emulator Execution
    • ELF loader reads and executes code
    • Cyclic inference loop: input → forward pass → output → repeat
    ↓
Outputs
```

## Binary Format Specification

The model is embedded as binary data with a specific layout:

### Header (28 bytes)
```
Offset | Field           | Type    | Value
-------|-----------------|---------|--------
0x00   | magic           | u32     | 0xDEADBEEF
0x04   | version         | u32     | 1
0x08   | model_type      | u32     | 1 (generator) or 2 (recognizer)
0x0C   | num_layers      | u32     | Number of layers
0x10   | total_weights   | u32     | Total float32 values in all weights
0x14   | total_biases    | u32     | Total float32 values in all biases
0x18   | reserved        | u32     | 0
```

### Layer Table (32 bytes × num_layers)
```
For each layer:
Offset | Field           | Type    | Description
-------|-----------------|---------|------------------
+0x00  | input_size      | u32     | Number of inputs
+0x04  | output_size     | u32     | Number of outputs
+0x08  | activation      | u32     | 0=ReLU, 1=Sigmoid, 2=Linear
+0x0C  | reserved1       | u32     | 0
+0x10  | weight_offset   | u32     | Byte offset (from data start)
+0x14  | bias_offset     | u32     | Byte offset (from data start)
+0x18  | reserved2       | u64     | 0
```

### Weights & Biases
```
All layer weights (float32), then all biases (float32)

Weight address = base + 28 + 32*num_layers + weight_offset
Bias address   = base + 28 + 32*num_layers + bias_offset

For dense layer computation:
    output[j] = relu/sigmoid(bias[j] + sum(input[i] * weight[i][j]))
```

## Memory Layout

```
Address    | Size      | Purpose
-----------|-----------|----------------------------------
0x00001000 | 60 KB     | Generated code section
0x00010000 | 1 MB      | Generator model (embedded binary)
0x00110000 | 256 KB    | Recognizer model (embedded binary)
0x00150000 | 4 KB      | Input buffer (255 floats for char input)
0x00151000 | 4 KB      | Activation buffer (ping)
0x00152000 | 4 KB      | Activation buffer (pong)
0x00153000 | 4 KB      | Output buffer (400 floats for 20×20 grid)
0x00200000 | 2 MB      | Framebuffer (80×25 characters, 20×20px each)
```

## Code Generation Details

### Input Mapping (One-Hot Encoding)

For character generation, input is a one-hot encoded vector:
- Input size: 255 (one per possible character)
- Only input[character_code] = 1.0
- All other inputs = 0.0

Generated code:
```asm
# Character code in a0
li a0, 65           # ASCII 'A'

# Clear input buffer
lui t0, 0x150000    # Load high bits of buffer address
# Zero 255 words...

# Set input[char_code] = 1.0
slli t1, a0, 2      # Byte offset
lui t2, 0x3F800     # 1.0 in IEEE 754
sw t2, (t0)(t1)     # input[char_code] = 1.0
```

### Dense Layer Computation

Nested loops for matrix multiplication with activation:

```asm
# Layer forward pass
# Input buffer at s1, output buffer at s2
# Model base address in s0

for j = 0 to output_size:
    # Load bias[j]
    fa0 = load_bias(s0, j)
    
    for i = 0 to input_size:
        # Load input[i] and weight[i][j]
        fa1 = input[i]
        fa2 = weight[i][j]
        
        # Accumulate: fa0 += fa1 * fa2
        fa0 += fa1 * fa2
    
    # Apply activation
    if activation == ReLU:
        fa0 = max(fa0, 0.0)    # Using FMAX.S
    else if activation == Sigmoid:
        fa0 = sigmoid_piecewise(fa0)
    
    # Store output[j]
    output[j] = fa0
```

### Output Mapping

Convert 400 output floats to 20×20 pixel grayscale grid:

```asm
for i = 0 to 400:
    # Load float output[i]
    fa0 = output[i]
    
    # Clamp to [0.0, 1.0]
    fa0 = max(fa0, 0.0)
    fa0 = min(fa0, 1.0)
    
    # Convert to byte (0-255)
    fa0 *= 255.0
    t5 = (uint)fa0
    
    # Write to framebuffer
    framebuffer[i] = t5
```

### Infinite Loop Structure

```asm
_start:
    li sp, 0xF000       # Stack pointer at safe location
    
inference_loop:
    li a0, 65           # Input: character code
    call map_input
    call run_forward_pass
    call map_output
    j inference_loop    # Jump back (infinite loop)
    
    # Unreachable code (for exit)
    li a0, 0
    li a7, 93           # SYS_exit
    ecall
```

## Activation Functions

### ReLU (Rectified Linear Unit)

**Implementation:** Using FMAX.S instruction
```asm
fmv.w.x fa1, zero    # fa1 = 0.0
fmax.s fa0, fa0, fa1 # fa0 = max(fa0, 0.0)
```

**Accuracy:** Exact (RISC-V native instruction)

### Sigmoid

**Implementation:** Piecewise linear approximation
```
if x ≤ -2.0:   sigmoid(x) ≈ 0.0
if -2 < x ≤ 0: sigmoid(x) ≈ 0.25 + 0.125*x
if 0 < x ≤ 2:  sigmoid(x) ≈ 0.75 + 0.125*x
if x > 2.0:    sigmoid(x) ≈ 1.0
```

**Accuracy:** Max error 0.25 vs true sigmoid (acceptable for character generation)

**Rationale:** Avoids exponential computation (not available in RV32I without complex libraries)

## Hard-Float ABI

### Why Hard-Float (-mabi=ilp32f)?

Soft-float ABI (-mabi=ilp32) passes floats in integer registers and requires soft-float library calls. These library functions are:
- Not supported by our emulator
- Inefficient for neural network workloads

Hard-float ABI (-mabi=ilp32f) passes floats in FP registers (fa0-fa7):
- Uses native RISC-V F extension instructions only
- Zero overhead compared to integer arithmetic
- Fully compatible with generated code

### Compiler Flags

```bash
# Assembly
riscv64-elf-as -march=rv32if -mabi=ilp32f -o program.o program.s

# Linking
riscv64-elf-ld -m elf32lriscv -T linker.ld -o program.elf program.o
```

## Code Generation Example

### Input Model (JSON)
```json
{
  "metadata": {
    "model_type": "generator",
    "version": 1,
    "architecture": "fully-connected",
    "precision": "float32"
  },
  "layers": [{
    "name": "dense_1",
    "input_size": 3,
    "output_size": 2,
    "activation": "relu",
    "weights": [[0.5, -0.5], [1.0, 2.0], [-1.0, 0.5]],
    "biases": [0.1, -0.2]
  }]
}
```

### Generated Code (Assembly)
```asm
.data
model_data_start:
    .incbin "model.bin"
model_data_end:

.text
_start:
    li sp, 0xF000
inference_loop:
    li a0, 65
    call map_input_generator
    call run_forward_pass
    call map_output_generator
    j inference_loop

layer_0_forward:
    # Dense computation
    # ...detailed assembly...
```

## Position-Independent Code

Generated code uses the `la` (load address) pseudo-instruction for all symbol references:

```asm
la s0, model_data_start    # Load address of model data
# Expands to:
# lui s0, <high20>
# addi s0, s0, <low12>
```

**Advantage:** Code works regardless of ELF load address

## Performance Characteristics

### Measured Performance

| Model Size | Layers | Parameters | ELF Size | Exec Time |
|-----------|--------|-----------|----------|-----------|
| Simple    | 1      | 8         | 5.6 KB   | 134 ms    |
| Small     | 2      | 316       | 7.2 KB   | 132 ms    |
| Medium    | 3      | 27,968    | 118 KB   | 132 ms    |
| Large     | 4      | 148,288   | 600 KB   | 133 ms    |

### Bottleneck: Loop-Based Multiplication

For output_size = 256, the weight computation requires:
```
inner_loop iterations = input_size × output_size
```

Current implementation: ~256 iterations per output element

**Optimization opportunity:** Use bit-shifting for powers of 2, hybrid algorithm for others.

## Validation

### Phase 3 Tests
- Single-layer networks (3→2 ReLU): ✅ PASS
- Multi-layer networks (255→256→256→400): ✅ PASS
- Loader integration (JSON→ELF→Execution): ✅ PASS
- Cyclic execution validation: ✅ PASS

### Numerical Accuracy
- ReLU: Exact (native instruction)
- Sigmoid: ±0.25 max error (acceptable)
- Forward pass: Matches Python reference

## Build & Test

### Build Emulator
```bash
cd projects/emulator
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
```

### Generate & Run Model
```bash
# Generate code from model
python3 model_compiler.py model.json model.s

# Assemble and link
riscv64-elf-as -march=rv32if -mabi=ilp32f -o model.o model.s
riscv64-elf-ld -m elf32lriscv -T linker.ld -o model.elf model.o

# Run on emulator
./emulator_runner model.elf
```

### Run Phase 4 Tests
```bash
python3 test_phase4_performance.py   # Performance profiling
python3 test_phase4_accuracy.py      # Numerical validation
```

## Known Limitations

1. **Multiplication Performance:** Loop-based approach (~256 iterations) could be optimized with bit-shifting
2. **Sigmoid Approximation:** ±0.25 error vs true sigmoid (acceptable trade-off)
3. **Fixed Memory Layout:** Addresses hardcoded (could be made dynamic with more header info)

## Future Improvements

1. **Phase 4:** Optimize multiplication, add performance instrumentation
2. **Phase 5:** GUI framebuffer integration, real-time rendering
3. **Phase 6:** TUI with keyboard input, interactive character exploration
4. **Phase 7:** Multi-model pipeline, batch inference

## References

- RISC-V ISA Specification: https://riscv.org/specifications/
- IEEE 754 Float Format: https://en.wikipedia.org/wiki/IEEE_754
- RISC-V F Extension: https://riscv.org/specifications/ (chapter 8)
