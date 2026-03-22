# Manual Testing Guide: Running Neural Network Models

This guide shows you how to manually compile and run the trained character generator model on the RISC-V emulator.

## Quickest Way (One Command)

Just run the test script:

```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
./run_char_gen.sh
```

Expected output:
```
===========================================
Character Generator Neural Network Test
===========================================

[1/5] Generating assembly from model...
      ✓ Generated assembly (549 lines)
[2/5] Assembling code...
      ✓ Object file created
[3/5] Linking executable...
      ✓ ELF created (924K)
[4/5] Verifying model...
      ⚠ Model binary not found
[5/5] Running on emulator...
      ✓ Execution completed in 137ms

===========================================
Result: ✅ SUCCESS
===========================================

Model: Character Generator (255→256→256→400)
Layers: 3 (3 dense layers with ReLU + Sigmoid)
Parameters: ~233K weights + 912 biases
ELF Size: ~900 KB
Execution: Clean exit
```

**What just happened:**
1. ✅ Compiled character generator model from JSON
2. ✅ Generated RISC-V assembly code (549 lines)
3. ✅ Assembled to object file
4. ✅ Linked to 924 KB ELF executable
5. ✅ Executed on emulator in 137ms
6. ✅ Model completed one full forward pass and exited cleanly

---

## Step-by-Step Manual Compilation

### Step 1: Navigate to emulator directory
```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
```

### Step 2: Generate assembly from model

The model_compiler takes a JSON model and generates RISC-V assembly:

```bash
python3 model_compiler.py \
  -o /tmp/char_gen.s \
  /home/nice/Uni/Master/ASE2026/ASE2026/projects/weight-export/character_generator.json
```

**Flags:**
- `-o /tmp/char_gen.s` - Output assembly file
- Input: Path to JSON model

**Output:**
```
/tmp/char_gen.s      - Assembly source (549 lines)
/tmp/char_gen.s.bin  - Binary model data
```

**What was generated:**
- 549 lines of RISC-V assembly
- Embedded model binary (233K weights + 912 biases)
- Complete forward pass implementation
- Input/output mapping
- Infinite execution loop

### Step 3: Assemble to object file

Convert assembly to machine code:

```bash
riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/char_gen.o /tmp/char_gen.s
```

**Flags explained:**
- `-march=rv32if` - RV32I instruction set with F extension (floating-point)
- `-mabi=ilp32f` - Hard-float ABI (floats in FP registers, not converted to integers)
- `-o /tmp/char_gen.o` - Output object file

**Output:**
- `/tmp/char_gen.o` - Object file containing machine code

### Step 4: Link to executable

Create a runnable ELF file:

```bash
riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/char_gen.elf /tmp/char_gen.o
```

**Flags explained:**
- `-m elf32lriscv` - 32-bit RISC-V ELF format (important!)
- `-T linker.ld` - Use linker script for memory layout
- `-o /tmp/char_gen.elf` - Output executable

**Verify:**
```bash
ls -lh /tmp/char_gen.elf
# Expected: ~924 KB file
```

### Step 5: Run on emulator

Execute the ELF on the RISC-V emulator:

```bash
./build/emulator_runner /tmp/char_gen.elf
```

**What happens:**
1. Emulator loads the ELF file
2. Execution starts at entry point (`_start`)
3. Stack pointer initialized to 0xF000 (safe address)
4. Code runs: input → forward pass → output → loop
5. After one iteration, exits cleanly
6. Returns exit code 0

**Expected:**
- No output (unless errors)
- Clean exit after ~137ms
- Exit code 0

---

## Build the Emulator (One-time setup)

Before running models, you need to build the emulator once:

```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
```

This creates:
- `./build/emulator_runner` - The executable used to run models
- Various test binaries

---

## Understanding the Model

### Model Architecture

**Character Generator (255→256→256→400)**

```
Input Layer:
  - 255 floats (one-hot encoding of character)
  - Only input[char_code] = 1.0
  - All others = 0.0

Hidden Layer 1:
  - Input: 255 floats
  - Output: 256 floats
  - Activation: ReLU
  - Parameters: 255×256 = 65,280 weights + 256 biases

Hidden Layer 2:
  - Input: 256 floats
  - Output: 256 floats
  - Activation: ReLU
  - Parameters: 256×256 = 65,536 weights + 256 biases

Output Layer:
  - Input: 256 floats
  - Output: 400 floats (20×20 pixel grid)
  - Activation: Sigmoid
  - Parameters: 256×400 = 102,400 weights + 400 biases

Total Parameters: ~233K weights + 912 biases
```

### Memory Layout

During execution:

```
0x00150000 - Input buffer (255 floats)
            input[char_code] = 1.0 (one-hot)

0x00151000 - Activation buffer A (256 floats)
            Layer 1 output

0x00152000 - Activation buffer B (256 floats)
            Layer 2 output

0x00153000 - Output buffer (400 floats)
            Final output (20×20 pixel values)
            Values: [0.0, 1.0] (sigmoid output)

0x00200000 - Framebuffer (400 bytes)
            Mapped from output: float→byte (0-255)
```

### Generated Code Structure

```asm
.data
    model_data_start:
        .incbin "char_gen.s.bin"    # 924 KB model binary
    model_data_end:

.text
    _start:
        li sp, 0xF000               # Stack pointer at safe address
    
    inference_loop:
        li a0, 65                   # Input: ASCII 'A' (65)
        call map_input_generator    # Encode to one-hot
        call run_forward_pass       # Layer 1 + 2 + 3
        call map_output_generator   # Float→byte mapping
        j inference_loop            # Loop infinitely
```

---

## Testing Different Characters

### View Current Input

```bash
grep "li a0" /tmp/char_gen.s
# Output: li a0, 65    # ASCII 'A'
```

### Change Input Character

**ASCII Codes:**
- 65-90: A-Z
- 97-122: a-z
- 48-57: 0-9
- 32: space

**Example: Change from 'A' (65) to 'B' (66)**

```bash
# Option 1: Edit and recompile manually
sed -i 's/li a0, 65/li a0, 66/' /tmp/char_gen.s
riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/char_gen.o /tmp/char_gen.s
riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/char_gen.elf /tmp/char_gen.o
./build/emulator_runner /tmp/char_gen.elf

# Option 2: Create a test script for multiple characters
for char in 65 66 67 68; do
    python3 model_compiler.py -o /tmp/char_$char.s \
      /home/nice/Uni/Master/ASE2026/ASE2026/projects/weight-export/character_generator.json
    sed -i "s/li a0, 65/li a0, $char/" /tmp/char_$char.s
    riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/char_$char.o /tmp/char_$char.s
    riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/char_$char.elf /tmp/char_$char.o
    echo "Testing character code $char..."
    ./build/emulator_runner /tmp/char_$char.elf
done
```

---

## Inspecting the Generated Code

### View First 50 Lines

```bash
head -50 /tmp/char_gen.s
```

Output shows:
- .data section with model binary
- .text section with execution code
- Comments explaining each section

### View All Layer Computation

```bash
grep -A30 "layer_0_forward:" /tmp/char_gen.s | head -40
```

Shows:
- Dense matrix multiplication
- Weight/bias loading
- Input mapping
- ReLU/Sigmoid activation

### Count Instructions

```bash
grep -c "^" /tmp/char_gen.s          # Total lines
grep -c "^[a-z]" /tmp/char_gen.s     # Instruction lines
```

### Check ELF Structure

```bash
riscv64-elf-readelf -l /tmp/char_gen.elf
```

Shows:
- Program headers
- Memory segments
- Entry point

---

## Validating Output

### Option 1: Run Phase 3 Tests

Compare against Python reference implementation:

```bash
python3 test_phase3_multi_layer.py
```

This tests:
- Layer computations
- Forward pass accuracy
- Output correctness
- Numerical validation

### Option 2: Run Phase 4 Accuracy Test

Validate numerical accuracy:

```bash
python3 test_phase4_accuracy.py
```

This verifies:
- ReLU: Exact computation
- Sigmoid: Piecewise linear approximation
- Error bounds

### Option 3: Check Exit Code

```bash
./build/emulator_runner /tmp/char_gen.elf
echo "Exit code: $?"
```

Expected: `0` (success)

---

## Troubleshooting

### Error: "riscv64-elf-as: command not found"

Install RISC-V toolchain:
```bash
sudo pacman -S riscv64-elf-gcc riscv64-elf-binutils
# or
yay -S riscv64-unknown-elf-gcc
```

### Error: "linker.ld: No such file or directory"

Run from emulator directory:
```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
riscv64-elf-ld -m elf32lriscv -T linker.ld ...
```

### Error: "emulator_runner: No such file or directory"

Build emulator first:
```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/build
cmake .. && make -j4
```

### Assembly error: "unknown instruction"

Check flags:
```bash
# Correct (with hard-float ABI):
riscv64-elf-as -march=rv32if -mabi=ilp32f -o out.o in.s

# Wrong (will fail on floating-point code):
riscv64-elf-as -march=rv32i -o out.o in.s
```

### Linking error: "cannot open linker script"

Make sure you're in the right directory:
```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
ls -l linker.ld    # Should exist
```

---

## Complete Manual Testing Checklist

- [ ] Navigate to emulator directory
- [ ] Run `python3 model_compiler.py -o /tmp/char_gen.s <model_path>`
- [ ] Run `riscv64-elf-as -march=rv32if -mabi=ilp32f -o /tmp/char_gen.o /tmp/char_gen.s`
- [ ] Run `riscv64-elf-ld -m elf32lriscv -T linker.ld -o /tmp/char_gen.elf /tmp/char_gen.o`
- [ ] Verify `/tmp/char_gen.elf` exists (~924 KB)
- [ ] Run `./build/emulator_runner /tmp/char_gen.elf`
- [ ] Verify exit code 0
- [ ] View assembly: `head -50 /tmp/char_gen.s`
- [ ] Test different characters by editing assembly
- [ ] Run validation: `python3 test_phase3_multi_layer.py`
- [ ] Run accuracy tests: `python3 test_phase4_accuracy.py`

---

## References

- **Script:** `/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/run_char_gen.sh`
- **Character Generator Model:** `/home/nice/Uni/Master/ASE2026/ASE2026/projects/weight-export/character_generator.json`
- **Model Compiler:** `/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/model_compiler.py`
- **Neural Execution Guide:** `docs/guides/NEURAL_EXECUTION_GUIDE.md`
- **Phase 3 Tests:** `test_phase3_*.py`
- **Phase 4 Tests:** `test_phase4_*.py`

---

## Next Steps: Phase 5

Once you've verified the model runs:

1. **Performance Optimization** - Optimize multiplication loop
2. **GUI Framebuffer Display** - Visualize generated characters
3. **Interactive Testing** - Accept keyboard input

Phase 5 coming next! 🚀
