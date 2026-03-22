# Interactive Neural Character Generation

## Overview

The neural character generator now works in **interactive mode** - matching the behavior of `static_char_gen.c` but using the trained neural network model instead of a static lookup table.

### Architecture

```
Input:  Register a0 (character code, set by emulator/user input)
        ↓
Encode: One-hot encoding (255 dimensions)
        ↓
Neural: Forward pass (3 layers: 255→256→256→400)
        Layer 1: ReLU activation
        Layer 2: ReLU activation
        Layer 3: Sigmoid activation
        ↓
Output: 400 floats (20×20 pixel grid)
        ↓
Map:    Float→Byte conversion (scale to 0-255)
        ↓
Write:  Framebuffer at 0x20000 (400 bytes)
        ↓
Loop:   Read a0 again, repeat infinitely
```

## Key Components

### 1. Interactive Model Compiler
**File:** `model_compiler_interactive.py`

Extends the standard model compiler to generate code that:
- Doesn't hardcode input (reads a0 each loop)
- Writes to framebuffer instead of output buffer
- Loops infinitely (like static_char_gen.c)

**Usage:**
```bash
python3 model_compiler_interactive.py \
  -o neural_model.s \
  ../weight-export/character_generator.json
```

**Output:**
- `neural_model.s` - Interactive RISC-V assembly (549 lines)
- `neural_model.s.bin` - Embedded model binary (921 KB)

### 2. Neural Character Generator Wrapper
**File:** `neural_char_gen.c`

Provides the interface matching `static_char_gen.c`:
- Infinite loop
- Reads character code from register `a0`
- Calls neural inference
- Writes to framebuffer at `0x20000` (400 bytes)

**Key Difference:**
- Static version: Lookup table (fast, deterministic)
- Neural version: Neural network computation (learned, approximate)

Both write to the same framebuffer location, enabling comparison.

### 3. Blackbox Test Suite
**File:** `test_neural_char_gen.py`

Tests the complete pipeline:
1. ✅ Model file exists
2. ✅ Interactive compiler exists
3. ✅ Model compiles to assembly (549 lines)
4. ✅ Assembly assembles to object file
5. ✅ Object links to ELF (921 KB)
6. ✅ ELF executes on emulator (infinite loop)

**Run:**
```bash
python3 blackbox_tests/test_neural_char_gen.py
```

## Usage

### Step 1: Compile Model
```bash
python3 model_compiler_interactive.py \
  -o /tmp/neural.s \
  ../weight-export/character_generator.json
```

### Step 2: Assemble
```bash
riscv64-elf-as -march=rv32if -mabi=ilp32f \
  -o /tmp/neural.o /tmp/neural.s
```

### Step 3: Link
```bash
riscv64-elf-ld -m elf32lriscv -T linker.ld \
  -o /tmp/neural.elf /tmp/neural.o
```

### Step 4: Run on Emulator
```bash
./build/emulator_runner /tmp/neural.elf
```

The model runs infinitely, reading character codes from `a0` and writing to framebuffer.

## Memory Layout

**During Execution:**
- Input buffer: 0x00150000 (255 floats, one-hot encoding)
- Activation buffer A: 0x00151000 (256 floats, layer 1 output)
- Activation buffer B: 0x00152000 (256 floats, layer 2 output)
- Output buffer: 0x00153000 (400 floats, layer 3 output)
- Framebuffer: **0x00020000** (400 bytes, final display pixels)

**Key:** Output is written directly to framebuffer at `0x20000`, matching `static_char_gen.c`.

## Generated Code

### Execution Loop
```asm
_start:
    li sp, 0xF000           # Stack pointer at safe address

inference_loop:
    # a0 contains character code (read by emulator)
    call map_input_generator    # Encode to one-hot
    call run_forward_pass       # Neural computation
    call map_output_generator   # Float→Byte, write to framebuffer
    j inference_loop            # Loop back
```

### Key Differences from Standard Compiler
1. **No hardcoded input:** Reads `a0` each iteration (was: `li a0, 65`)
2. **Framebuffer output:** Writes to `0x20000` (was: `0x00153000`)
3. **Infinite loop:** Like `static_char_gen.c` (was: exit after one iteration)

## Performance

**Single Inference:**
- ~137ms per forward pass
- Bottleneck: Loop-based multiplication (256 iterations for 256×256 weights)

**Optimization Opportunity:**
- Bit-shifting for powers of 2 (50%+ faster)
- Planned for Phase 5

## Testing Different Characters

**Interactive mode allows testing different characters without recompilation:**

```bash
# Character 'A' (65)
./build/emulator_runner neural.elf --char 65

# Character 'B' (66)
./build/emulator_runner neural.elf --char 66

# Character '0' (48)
./build/emulator_runner neural.elf --char 48
```

Or edit the assembly if using raw execution:
```bash
sed -i 's/li a0, 65/li a0, 66/' neural.s
```

## Comparison with Static Version

| Aspect | Static | Neural |
|--------|--------|--------|
| Input | Character code → lookup | Character code → neural input |
| Processing | Table lookup (instant) | Forward pass (137ms) |
| Output | Exact pixels (trained font) | Learned approximation |
| Memory | ~547 KB (font table) | ~921 KB (model weights) |
| Computation | O(1) per character | O(n) per forward pass |
| Variability | Deterministic | Learned patterns |

**Use Case:**
- Static: Fast, exact character reproduction
- Neural: Demonstrates learned generation, comparison baseline

## Next Steps: GUI Integration

### Phase 5 Plans:
1. **Display neural output** with `--gui` switch
2. **Show side-by-side comparison** of neural vs static output
3. **Interactive keyboard input** for testing multiple characters
4. **Real-time framebuffer rendering**

### Example:
```bash
# Display neural character generator
./build/emulator_runner neural.elf --gui

# Compare with static
./build/emulator_runner static_char_gen.elf --gui
```

## Files Summary

| File | Purpose |
|------|---------|
| `model_compiler_interactive.py` | Generate interactive assembly |
| `neural_char_gen.c` | C wrapper for interactive loop |
| `test_neural_char_gen.py` | Blackbox test suite |
| `INTERACTIVE_NEURAL_CHARGEN.md` | This documentation |

## Test Results

```
======================================================================
NEURAL CHARACTER GENERATION BLACKBOX TESTS
======================================================================

✓ Model file exists
✓ Interactive compiler exists
✓ Compile model to assembly
✓ Assemble code to object file
✓ Link to ELF executable
✓ Execute on emulator

======================================================================
RESULTS: 6 passed, 0 failed
======================================================================
```

## Technical Details

### Hard-Float ABI
Uses `-mabi=ilp32f` for efficient floating-point computation:
- Floats passed in FP registers (fa0-fa7)
- No soft-float library calls
- Native RISC-V F extension instructions

### Position-Independent Code
Uses `la` pseudo-instruction for all symbol references:
```asm
la s0, model_data_start    # Loads address dynamically
```

Allows ELF to load at any address in memory.

### Binary Format
```
Header (28 bytes)          - Magic, version, model metadata
Layer Table (32B × 3)      - Input/output sizes, activation types
Weights (binary)           - All weights (float32)
Biases (binary)            - All biases (float32)
```

Total embedded model size: ~921 KB

## Debugging

**Assembly not assembling?**
```bash
# Check errors
riscv64-elf-as -march=rv32if -mabi=ilp32f -o neural.o neural.s 2>&1 | head -20
```

**ELF not linking?**
```bash
# Verify object file
file neural.o
riscv64-elf-readelf -h neural.o
```

**Not executing on emulator?**
```bash
# Check ELF format
riscv64-elf-readelf -l neural.elf | head -20

# Check memory layout
riscv64-elf-objdump -h neural.elf
```

## References

- **Model Compiler:** `model_compiler.py` (standard, non-interactive)
- **Static Char Gen:** `static_char_gen.c` (lookup-based)
- **Neural Execution Guide:** `docs/guides/NEURAL_EXECUTION_GUIDE.md`
- **Quick Start:** `../../QUICK_START.md`
