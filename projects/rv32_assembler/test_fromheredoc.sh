#!/bin/bash
cat > test_hd.s << 'ASM'
addi x1, x0, 42
add x2, x1, x1
sub x3, x2, x1
and x4, x2, x3
or x5, x3, x4
xor x6, x4, x5
ASM
echo "File created with $(wc -l < test_hd.s) lines"
head -1 test_hd.s | od -c
cargo run --quiet --bin rv32as -- test_hd.s
