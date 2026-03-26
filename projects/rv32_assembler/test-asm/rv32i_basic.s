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
