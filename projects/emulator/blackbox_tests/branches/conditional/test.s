# Conditional Branch Test
# Tests BEQ, BNE, BLT, BGE with different outcomes

.section .text
.globl _start

_start:
    # Test BEQ (branch if equal)
    li t0, 42
    li t1, 42
    bne t0, t1, fail       # Should not branch (they're equal)
    
    # Test BNE (branch if not equal)
    li t2, 10
    li t3, 20
    beq t2, t3, fail       # Should not branch (they're not equal)
    
    # Test BLT (branch if less than, signed)
    li t4, -5
    li t5, 10
    bge t4, t5, fail       # Should not branch (-5 < 10)
    
    # Test BGE (branch if greater or equal, signed)
    li t0, 100
    li t1, 50
    blt t0, t1, fail       # Should not branch (100 >= 50)
    
    # Test BLTU (branch if less than, unsigned)
    li t2, 5
    li t3, 10
    bgeu t2, t3, fail      # Should not branch (5 < 10 unsigned)
    
    # Test BGEU (branch if greater or equal, unsigned)
    li t4, 200
    li t5, 100
    bltu t4, t5, fail      # Should not branch (200 >= 100 unsigned)
    
    # All tests passed
    li a7, 64
    li a0, 1
    la a1, pass_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 0
    ecall

fail:
    # Print FAIL and exit with code 1
    li a7, 64
    li a0, 1
    la a1, fail_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 1
    ecall

.section .data
pass_msg:
    .string "PASS\n"
fail_msg:
    .string "FAIL\n"
