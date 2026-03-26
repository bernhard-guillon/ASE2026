#!/bin/bash
set -e

TEST_FILE="test_simple.s"
RUST_OUT="rust_output.o"
GNU_OUT="gnu_output.o"

# Create test assembly
cat > $TEST_FILE << 'ASM'
# RV32I basic operations
addi x1, x0, 42
add x2, x1, x1
sub x3, x2, x1
and x4, x2, x3
or x5, x3, x4
xor x6, x4, x5

# Loads and stores
lw x7, 0(x6)
sh x7, 2(x6)
sb x5, 1(x6)

# Branches and jumps
beq x1, x2, 8
bne x3, x4, 4
jal x31, 100
ASM

# Assemble with our Rust assembler
echo "Assembling with Rust assembler..."
cargo run --quiet --bin rv32as -- $TEST_FILE -o $RUST_OUT

# Assemble with GNU assembler (if available)
if command -v riscv64-elf-as &> /dev/null; then
    echo "Assembling with GNU assembler..."
    riscv64-elf-as -march=rv32i -mabi=ilp32 $TEST_FILE -o gnu_tmp.o
    objcopy -O binary -j .text gnu_tmp.o $GNU_OUT
    
    # Compare
    echo "Comparing outputs..."
    if cmp -l $RUST_OUT $GNU_OUT > diff.txt; then
        echo "✓ PARITY: Outputs are identical!"
        rm -f $TEST_FILE $RUST_OUT $GNU_OUT gnu_tmp.o diff.txt
        exit 0
    else
        echo "✗ PARITY MISMATCH:"
        hexdump -C $RUST_OUT
        echo "---"
        hexdump -C $GNU_OUT
        echo "First difference at byte:"
        head -1 diff.txt
        exit 1
    fi
else
    echo "GNU assembler not found, skipping parity check"
    echo "Rust output:"
    hexdump -C $RUST_OUT
    rm -f $TEST_FILE $RUST_OUT
fi
