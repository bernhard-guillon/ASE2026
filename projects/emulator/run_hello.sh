#!/bin/bash
# Script to compile and run Hello World with RV32I emulator

set -e

echo "=== RV32I Hello World Compilation and Execution ==="
echo

# Note: This requires the RISC-V GNU toolchain to be installed
# Install with: sudo apt install gcc-riscv64-unknown-elf

# Check if toolchain is available
if ! command -v riscv32-unknown-elf-as &> /dev/null; then
    echo "ERROR: RISC-V toolchain not found"
    echo "Please install with:"
    echo "  sudo apt install gcc-riscv64-unknown-elf"
    echo "  or download from: https://github.com/riscv-collab/riscv-gnu-toolchain"
    echo
    echo "=== Running demo with hardcoded instructions instead ==="
    echo
    cd build && ./hello_world_demo
    exit 0
fi

echo "Step 1: Assembling hello.s..."
riscv32-unknown-elf-as -march=rv32i -mabi=ilp32 -o hello.o hello.s

echo "Step 2: Linking..."
riscv32-unknown-elf-ld -m elf32lriscv -T linker.ld -o hello.elf hello.o

echo "Step 3: Creating binary image..."
riscv32-unknown-elf-objcopy -O binary hello.elf hello.bin

echo "Step 4: Disassembling for verification..."
riscv32-unknown-elf-objdump -d hello.elf > hello.dis
echo "Disassembly saved to hello.dis"

echo
echo "Step 5: Running in emulator..."
cd build && ./emulator_runner ../hello.bin

echo
echo "Done!"
