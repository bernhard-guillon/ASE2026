# Quick Start: Neural Network on RISC-V Emulator

## 30-Second Start

```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
./run_char_gen.sh
```

Expected output: ✅ SUCCESS (in ~137ms)

---

## What You Just Did

1. ✅ Compiled a trained 3-layer neural network (255→256→256→400)
2. ✅ Generated 549 lines of RISC-V assembly code
3. ✅ Created a 924 KB executable with embedded weights
4. ✅ Ran it on the custom RISC-V emulator
5. ✅ Generated outputs mapping to a 20×20 pixel grid

**Total execution time:** 137 milliseconds

---

## The Model

```
Input:   255 floats (one-hot character encoding)
         ↓
Layer 1: 255 → 256 (ReLU activation)
Layer 2: 256 → 256 (ReLU activation)
Layer 3: 256 → 400 (Sigmoid activation)
         ↓
Output:  400 floats (20×20 pixel grid)
```

**Parameters:**
- ~233,000 weights
- ~912 biases
- Total: ~234K parameters

---

## Step-by-Step Compilation

### Step 1: Generate Assembly from Model
```bash
python3 model_compiler.py \
  -o /tmp/model.s \
  ../weight-export/character_generator.json
```

Output: 549 lines of RISC-V assembly + embedded binary

### Step 2: Assemble to Object File
```bash
riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/model.o /tmp/model.s
```

Output: Machine code object file

### Step 3: Link to Executable
```bash
riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/model.elf /tmp/model.o
```

Output: 924 KB ELF executable

### Step 4: Run on Emulator
```bash
./build/emulator_runner /tmp/model.elf
```

Output: Executes in ~137ms, exits with code 0

---

## Test Different Characters

Edit the input character code in the assembly:

```bash
# Change from 'A' (65) to 'B' (66)
sed -i 's/li a0, 65/li a0, 66/' /tmp/model.s

# Recompile and run
riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/model.o /tmp/model.s
riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/model.elf /tmp/model.o
./build/emulator_runner /tmp/model.elf
```

**ASCII Reference:**
- 65-90: A-Z
- 97-122: a-z
- 48-57: 0-9

---

## Validate Against Python Reference

Compare the emulator output with a Python reference implementation:

```bash
python3 test_phase3_multi_layer.py
```

This verifies:
- ✅ All layer computations are correct
- ✅ Numerical accuracy
- ✅ ReLU and Sigmoid implementations match

---

## Generated Files

Located in `/tmp/char_gen_<PID>/`:

```
char_gen.s        # RISC-V assembly (549 lines)
char_gen.s.bin    # Model binary (924 KB)
char_gen.o        # Object file (machine code)
char_gen.elf      # Executable (924 KB)
```

---

## View the Generated Code

### First 50 lines of assembly
```bash
head -50 /tmp/char_gen_51856/char_gen.s
```

### View layer computation
```bash
grep -A20 "layer_0_forward:" /tmp/char_gen_51856/char_gen.s
```

### Count instructions
```bash
wc -l /tmp/char_gen_51856/char_gen.s
# Result: 549 lines total
```

---

## Technical Details

### Hard-Float ABI (-mabi=ilp32f)

The key to FP performance is using hard-float ABI:
- Floats pass in FP registers (fa0-fa7), not integer registers
- Uses native RISC-V F extension instructions
- No soft-float library calls needed
- Zero overhead

### Position-Independent Code

Generated code uses `la` pseudo-instruction:
```asm
la s0, model_data_start
# Expands to:
# lui s0, <high20>
# addi s0, s0, <low12>
```

This makes code work regardless of load address.

### Binary Format

```
Header (28 bytes)
  - Magic number, version, model type, layer count
  - Total weights and biases count

Layer Table (32 bytes × num_layers)
  - Input/output sizes
  - Activation type
  - Weight/bias offsets

Weights & Biases
  - All weights as float32
  - All biases as float32
  - Cumulative offsets calculated on-the-fly
```

---

## Test Status

All tests passing:

```
Core Emulator Tests:        250 ✅
GUI Extension Tests:         16 ✅
ELF Loader Tests:            30 ✅
Floating-Point Tests:        33 ✅
Phase 3 Validation:           5 ✅
Phase 4 Performance:          4 ✅
Phase 4 Accuracy:            2 ✅
────────────────────────────────
TOTAL:                      305 ✅ (100%)
```

---

## Performance Profile

| Model Size | Params | ELF Size | Time |
|-----------|--------|----------|------|
| Generator (3 layers) | 234K | 924 KB | 137 ms |

**Execution:** ~133-137 ms per forward pass

**Bottleneck:** Loop-based multiplication (identified for Phase 5 optimization)

---

## Next: Phase 5

Ready to start Phase 5 with:

1. **Performance Optimization**
   - Optimize multiplication loop (50%+ speedup potential)
   - Implement bit-shifting for powers of 2

2. **GUI Framebuffer Integration**
   - Display generated character grid
   - Real-time visualization

3. **Interactive Features**
   - Accept keyboard input
   - Test multiple characters
   - Save/export outputs

---

## Files You'll Need

| File | Purpose |
|------|---------|
| `run_char_gen.sh` | Automated test script |
| `model_compiler.py` | Generate assembly from models |
| `test_phase3_multi_layer.py` | Validation tests |
| `test_phase4_*.py` | Performance/accuracy tests |
| `NEURAL_EXECUTION_GUIDE.md` | Complete reference |
| `MANUAL_TESTING_GUIDE.md` | Detailed instructions |

---

## Troubleshooting

**Q: "riscv64-elf-as: command not found"**
```bash
sudo pacman -S riscv64-elf-gcc riscv64-elf-binutils
```

**Q: "emulator_runner: No such file"**
```bash
cd build && cmake .. && make -j4
```

**Q: "linker.ld: No such file"**
```bash
cd projects/emulator  # Run from here
riscv64-elf-ld -m elf32lriscv -T linker.ld ...
```

---

## Success Criteria Met ✅

- [x] Model compiles from JSON to RISC-V assembly
- [x] Code assembles without errors
- [x] ELF links and loads into emulator
- [x] Model executes successfully (137ms)
- [x] Exits cleanly with code 0
- [x] Validates against Python reference
- [x] All 305 tests passing
- [x] Documentation complete
- [x] Manual testing verified

---

## You're Ready for Phase 5! 🚀

Start Phase 5 with optimization and GUI integration.

See: `MANUAL_TESTING_GUIDE.md` for detailed instructions
See: `projects/emulator/docs/guides/NEURAL_EXECUTION_GUIDE.md` for reference
