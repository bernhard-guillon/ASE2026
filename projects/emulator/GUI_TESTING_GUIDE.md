# Manual GUI Testing Guide: Neural Character Generator

**Quick Start:** Follow Steps 1-5 below to see the neural character generator in action with interactive keyboard input.

---

## Quick Test (Copy & Paste)

```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator

# Step 1: Compile model to assembly
python3 model_compiler_interactive.py -o neural.s ../weight-export/character_generator.json

# Step 2: Assemble to object file
riscv64-elf-as -march=rv32if -mabi=ilp32f -o neural.o neural.s

# Step 3: Link to ELF executable
riscv64-elf-ld -m elf32lriscv -T linker.ld -o neural.elf neural.o

# Step 4: Run with GUI mode
./build/emulator_runner neural.elf --gui
```

Then press any key to test!

---

## Detailed Step-by-Step Instructions

### Prerequisites

Ensure you have:
- RISC-V toolchain installed: `riscv64-elf-gcc`, `riscv64-elf-as`, `riscv64-elf-ld`
- Emulator built: `./build/emulator_runner`
- Character generator model: `../weight-export/character_generator.json`

**Check prerequisites:**
```bash
which riscv64-elf-as
which riscv64-elf-ld
ls -la projects/emulator/build/emulator_runner
ls -la projects/weight-export/character_generator.json
```

### Step 1: Compile Model to Assembly

The model compiler converts the neural network JSON into RISC-V assembly code.

```bash
cd projects/emulator

python3 model_compiler_interactive.py \
  -o neural.s \
  ../weight-export/character_generator.json
```

**What happens:**
- Reads the trained neural network weights from JSON
- Generates ~550 lines of RISC-V assembly
- Implements 3-layer neural network (input → ReLU → ReLU → output)
- Reads input from register a0 each iteration
- Writes output to framebuffer at 0x20000
- Uses hard-float ABI (-mabi=ilp32f) for efficient float operations

**Output:** `neural.s` file with assembly code

**Verify:**
```bash
ls -la neural.s
wc -l neural.s  # Should show ~550 lines
head -20 neural.s  # View first few instructions
```

### Step 2: Assemble to Object File

Convert assembly to machine code object file.

```bash
riscv64-elf-as \
  -march=rv32if \
  -mabi=ilp32f \
  -o neural.o \
  neural.s
```

**Flags explained:**
- `-march=rv32if`: RISC-V 32-bit with F extension (floating-point)
- `-mabi=ilp32f`: Hard-float ABI (floats in FP registers, not integer registers)
- `-o neural.o`: Output file name

**Output:** `neural.o` binary object file (~30-50 KB)

**Verify:**
```bash
file neural.o  # Should show "ELF 32-bit LSB relocatable"
ls -lh neural.o
```

### Step 3: Link to ELF Executable

Link the object file into a complete executable using the linker script.

```bash
riscv64-elf-ld \
  -m elf32lriscv \
  -T linker.ld \
  -o neural.elf \
  neural.o
```

**Flags explained:**
- `-m elf32lriscv`: 32-bit RISC-V little-endian format
- `-T linker.ld`: Use linker script for memory layout
- `-o neural.elf`: Output executable name

**Output:** `neural.elf` executable (~900 KB with all symbols)

**Verify:**
```bash
file neural.elf  # Should show "ELF 32-bit LSB executable"
ls -lh neural.elf
riscv64-elf-objdump -h neural.elf  # View sections
```

### Step 4: Run Emulator with GUI

Execute the neural character generator in interactive GUI mode.

```bash
./build/emulator_runner neural.elf --gui
```

**What happens:**
- Emulator loads the ELF file
- Initializes RISC-V CPU with entry point
- Enters GUI mode (raw terminal mode for keyboard capture)
- Displays initial blank framebuffer (20×20 grid)
- Waits for keyboard input

**Output:** 20×20 character grid displayed in terminal

```
════════════════════════════════════════════════════════════════════════════════
GUI mode active. Press any key to change character. Ctrl+C to exit.
Starting with character code 0...

(blank 20x20 grid initially)

Press keys to change character:
```

### Step 5: Test Different Characters

While the emulator is running in GUI mode:

**Press different keys:**

| Key | ASCII | Result |
|-----|-------|--------|
| `A` | 65 | Shows neural-generated letter 'A' |
| `Z` | 90 | Shows neural-generated letter 'Z' |
| `a` | 97 | Shows neural-generated letter 'a' |
| `0` | 48 | Shows neural-generated number '0' |
| Space | 32 | Shows neural-generated space |
| `!` | 33 | Shows neural-generated exclamation |

**For each character:**
1. Press the key
2. Emulator reads ASCII code from a0 register
3. Neural network generates output (20×20 pixels)
4. Framebuffer rendered to terminal
5. Display updates with the character pattern

**Example output (character 'A'):**
```
    #########
    #       #
    #       #
    #########
    #       #
    #       #
    #       #
    
    (etc, showing 20x20 grid)
```

### Step 6: Exit GUI Mode

Press `Ctrl+C` to exit the interactive GUI.

```
Key: 'A' (ASCII 65)
Key: 'Z' (ASCII 90)
^C
Interrupt received. Exiting...

GUI mode closed.
```

---

## Testing Different Characters

### ASCII Printable Characters to Test

**Uppercase Letters (65-90):**
```
A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
65-90
```
Test: Press `A` then `M` then `Z`

**Lowercase Letters (97-122):**
```
a b c d e f g h i j k l m n o p q r s t u v w x y z
97-122
```
Test: Press `a` then `m` then `z`

**Digits (48-57):**
```
0 1 2 3 4 5 6 7 8 9
48-57
```
Test: Press `0` through `9`

**Punctuation (33-47, 58-64):**
```
! " # $ % & ' ( ) * + , - . /
: ; < = > ? @
33-47, 58-64
```
Test: Press `!` `,` `?`

**Special Characters (91-96, 123-126):**
```
[ \ ] ^ _ ` { | } ~
91-96, 123-126
```
Test: Press `[` `]` `{` `}`

---

## What You'll See

### Initial State
```
GUI mode active. Press any key to change character. Ctrl+C to exit.
Starting with character code 0...

(blank 20x20 grid)
```

### After Pressing 'A'
```
Key: 'A' (ASCII 65)

████████  ████████
█       █       █
█       █       █
█████████       █
█       █       █
█       █       █
█       █       █
█       █       █
(rest of 20x20 grid showing neural-generated 'A' pattern)
```

### After Pressing 'Z'
```
Key: 'Z' (ASCII 90)

████████████████████
           █
        █
     █
  █
█
████████████████████
(rest of 20x20 grid showing neural-generated 'Z' pattern)
```

### Performance Indicator
Each key press triggers:
1. One neural network forward pass (~133ms)
2. Framebuffer rendering (~5ms)
3. Display update (~10ms)

You'll notice slight delay (~150ms) between pressing a key and seeing the output. This is the neural computation time.

---

## Troubleshooting

### Issue: "emulator_runner: command not found"

**Solution:** Build the emulator first
```bash
cd projects/emulator/build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
```

### Issue: "Error: Could not open file neural.elf"

**Solution:** Verify the ELF file exists
```bash
ls -la neural.elf
# If missing, re-run Steps 1-3
```

### Issue: "Terminal doesn't respond to keyboard"

**Solution:** 
1. Try pressing keys more deliberately
2. Check if raw terminal mode is enabled
3. Restart terminal or press Ctrl+C and try again

### Issue: "Terminal gets corrupted after Ctrl+C"

**Solution:** Restore terminal with:
```bash
reset
# or
stty sane
```

### Issue: "Program hangs (no output)"

**Solution:**
- Press a key to trigger neural computation
- Press Ctrl+C to exit
- Check if model file exists: `ls -la ../weight-export/character_generator.json`

### Issue: "Characters appear blank"

**Solution:**
- Model may need retraining
- Check framebuffer address is correct (0x20000)
- Verify output scaling (float → byte conversion)
- Try different characters to see if it's model-specific

### Issue: "Assembly/linking failed"

**Solution:** Check ABI flags match exactly
```bash
# Make sure you use these exact flags:
riscv64-elf-as -march=rv32if -mabi=ilp32f -o neural.o neural.s
riscv64-elf-ld -m elf32lriscv -T linker.ld -o neural.elf neural.o
```

---

## Advanced Testing

### Test Single Character (Non-Interactive)

To test a single character without interactive mode:

```bash
./build/emulator_runner neural.elf --char A
```

**Output:** Shows just the framebuffer for character 'A', then exits

### Compare with Static Character Generator

```bash
# Test neural version
./build/emulator_runner neural.elf --char A

# Compare with static version (if available)
# (static_char_gen.c provides a reference)
```

### Performance Profiling

Monitor how long each inference takes:

```bash
# In interactive GUI mode, press keys and note the delay
# Each inference takes ~133ms
# This is shown in the neural architecture but can be optimized
```

### View Generated Assembly

To inspect the generated RISC-V code:

```bash
# View first 50 lines
head -50 neural.s

# View around a specific section (e.g., input encoding)
grep -n "input" neural.s | head -10

# Count total lines
wc -l neural.s

# View with line numbers
cat -n neural.s | less
```

### Inspect ELF Sections

```bash
# Show all sections
riscv64-elf-objdump -h neural.elf

# Show disassembly
riscv64-elf-objdump -d neural.elf | head -100

# Show symbols
riscv64-elf-nm neural.elf | head -20
```

---

## Complete Workflow Summary

```bash
#!/bin/bash
# Complete testing workflow

cd projects/emulator

# 1. Compile
echo "=== Step 1: Compiling model ==="
python3 model_compiler_interactive.py -o neural.s ../weight-export/character_generator.json

# 2. Assemble
echo "=== Step 2: Assembling to object ==="
riscv64-elf-as -march=rv32if -mabi=ilp32f -o neural.o neural.s

# 3. Link
echo "=== Step 3: Linking to ELF ==="
riscv64-elf-ld -m elf32lriscv -T linker.ld -o neural.elf neural.o

# 4. Show file info
echo "=== File Info ==="
ls -lh neural.elf
file neural.elf

# 5. Run GUI
echo "=== Starting GUI (press any key to test) ==="
./build/emulator_runner neural.elf --gui
```

Save as `test_gui.sh` and run:
```bash
chmod +x test_gui.sh
./test_gui.sh
```

---

## What Each Component Does

### model_compiler_interactive.py
- **Input:** JSON file with neural network weights
- **Output:** RISC-V assembly code
- **Does:** Generates code that reads a0 each iteration, computes neural network, writes to framebuffer, loops infinitely

### neural.s (Generated Assembly)
- **Input:** Register a0 (character code)
- **Output:** 400 bytes written to framebuffer at 0x20000
- **Does:** Implements 3-layer neural network:
  1. One-hot encode input (255 dimensions)
  2. Multiply by first layer weights (255→256)
  3. Apply ReLU activation
  4. Multiply by second layer weights (256→256)
  5. Apply ReLU activation
  6. Multiply by third layer weights (256→400)
  7. Scale floats to bytes (0-255)
  8. Write to framebuffer
  9. Loop back

### emulator_runner (GUI)
- **Input:** ELF executable, --gui flag, keyboard input
- **Output:** Terminal display of framebuffer
- **Does:**
  1. Captures keyboard input (raw terminal mode)
  2. Stores ASCII code in register a0
  3. Executes emulator for ~130K steps
  4. Renders framebuffer to terminal (20×20 grid)
  5. Updates display in real-time

### FramebufferRenderer
- **Input:** Memory contents at 0x20000 (400 bytes)
- **Output:** 20×20 character grid to terminal
- **Does:** Converts each byte to '#' (if > 127) or ' ' (if ≤ 127)

---

## Key Insights

### Why 133ms per inference?
- Loop-based matrix multiplication takes time
- 256×256 matrix requires ~256 iterations
- Could be optimized with bit-shifting (Phase 6 goal)

### Why 20×20 grid?
- 400 bytes output from neural network
- 400 = 20 × 20 (perfect square for grid display)
- Terminal character resolution naturally maps to this

### Why framebuffer at 0x20000?
- Easy to access from generated code
- Doesn't conflict with other memory regions
- Matches static_char_gen.c interface (allows comparison)

### Why hard-float ABI?
- Neural network uses floating-point computation
- Hard-float (-mabi=ilp32f) passes floats in FP registers
- Soft-float would require external library (not available in bare-metal)
- Native RISC-V F extension is efficient

---

## Next Steps

After testing the GUI, you can:

1. **Compare outputs** - Run both neural and static versions, compare patterns
2. **Test performance** - Note the 133ms per inference, identify optimization opportunities
3. **Expand character set** - Retrain model for digits, symbols, special characters
4. **Optimize code** - Implement bit-shifting for 50%+ speedup (Phase 6)
5. **Enhance visuals** - Add color support, increase resolution (Phase 6)

---

## References

- **PHASE5_GUI_INTEGRATION.md** - Full GUI architecture documentation
- **INTERACTIVE_NEURAL_CHARGEN.md** - Interactive model details
- **MANUAL_TESTING_GUIDE.md** - Alternative manual testing approach
- **model_compiler_interactive.py** - Compiler source code
- **test_phase5_gui_integration.py** - Automated test suite
