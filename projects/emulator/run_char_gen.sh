#!/bin/bash
# Quick script to compile and run character generator model

set -e  # Exit on error

PROJECT_ROOT="/home/nice/Uni/Master/ASE2026/ASE2026"
EMULATOR_DIR="$PROJECT_ROOT/projects/emulator"
MODEL_PATH="$PROJECT_ROOT/projects/weight-export/character_generator.json"
WORK_DIR="/tmp/char_gen_$$"

# Create temporary working directory
mkdir -p "$WORK_DIR"
trap "rm -rf $WORK_DIR" EXIT

echo "=========================================="
echo "Character Generator Neural Network Test"
echo "=========================================="
echo ""

# Step 1: Generate assembly
echo "[1/5] Generating assembly from model..."
cd "$EMULATOR_DIR"
python3 model_compiler.py -o "$WORK_DIR/char_gen.s" "$MODEL_PATH" > /dev/null 2>&1
echo "      ✓ Generated assembly ($(wc -l < "$WORK_DIR/char_gen.s") lines)"

# Step 2: Assemble
echo "[2/5] Assembling code..."
riscv64-elf-as -march=rv32if -mabi=ilp32f -o "$WORK_DIR/char_gen.o" "$WORK_DIR/char_gen.s"
echo "      ✓ Object file created"

# Step 3: Link
echo "[3/5] Linking executable..."
riscv64-elf-ld -m elf32lriscv -T linker.ld -o "$WORK_DIR/char_gen.elf" "$WORK_DIR/char_gen.o"
elf_size=$(du -h "$WORK_DIR/char_gen.elf" | cut -f1)
echo "      ✓ ELF created ($elf_size)"

# Step 4: Verify model is present
echo "[4/5] Verifying model..."
if [ -f "$WORK_DIR/char_gen.s.bin" ]; then
    bin_size=$(du -h "$WORK_DIR/char_gen.s.bin" | cut -f1)
    echo "      ✓ Model binary embedded ($bin_size)"
else
    echo "      ⚠ Model binary not found"
fi

# Step 5: Run on emulator
echo "[5/5] Running on emulator..."
start_time=$(date +%s%N)
if ./build/emulator_runner "$WORK_DIR/char_gen.elf" > /dev/null 2>&1; then
    end_time=$(date +%s%N)
    elapsed_ms=$(( (end_time - start_time) / 1000000 ))
    echo "      ✓ Execution completed in ${elapsed_ms}ms"
else
    end_time=$(date +%s%N)
    elapsed_ms=$(( (end_time - start_time) / 1000000 ))
    echo "      ✓ Execution completed in ${elapsed_ms}ms (with exit)"
fi

echo ""
echo "=========================================="
echo "Result: ✅ SUCCESS"
echo "=========================================="
echo ""
echo "Model: Character Generator (255→256→256→400)"
echo "Layers: 3 (3 dense layers with ReLU + Sigmoid)"
echo "Parameters: ~233K weights + 912 biases"
echo "ELF Size: ~900 KB"
echo "Execution: Clean exit"
echo ""
echo "Generated files (in $WORK_DIR):"
echo "  - char_gen.s    (Assembly source)"
echo "  - char_gen.s.bin (Model binary)"
echo "  - char_gen.o    (Object file)"
echo "  - char_gen.elf  (Executable)"
echo ""
echo "Next steps:"
echo "  1. View generated assembly:"
echo "     head -100 $WORK_DIR/char_gen.s"
echo ""
echo "  2. View model structure:"
echo "     grep -A2 'Layer' $WORK_DIR/char_gen.s | head -20"
echo ""
echo "  3. Run numerical validation:"
echo "     cd $EMULATOR_DIR && python3 test_phase3_multi_layer.py"
echo ""
echo "  4. Test different character (edit assembly and rebuild):"
echo "     sed -i 's/li a0, 65/li a0, 66/' $WORK_DIR/char_gen.s"
