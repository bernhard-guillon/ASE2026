# Shift Operations Test
# Tests SLL, SRL, SRA with various amounts

.section .text
.globl _start

_start:
    # Test SLL: 1 << 4 = 16
    li t0, 1
    li t1, 4
    sll t2, t0, t1        # t2 = 1 << 4 = 16
    li t3, 16
    bne t2, t3, fail
    
    # Test SRL: 16 >> 2 = 4
    li t0, 16
    li t1, 2
    srl t2, t0, t1        # t2 = 16 >> 2 = 4
    li t3, 4
    bne t2, t3, fail
    
    # Test SRA with positive: 32 >> 2 = 8
    li t0, 32
    li t1, 2
    sra t2, t0, t1        # t2 = 32 >> 2 = 8
    li t3, 8
    bne t2, t3, fail
    
    # Test SRA with negative: -32 >> 2 = -8 (sign extended)
    li t0, -32
    li t1, 2
    sra t2, t0, t1        # t2 = -32 >> 2 = -8
    li t3, -8
    bne t2, t3, fail
    
    # Test shift masking: shift by 36 is same as shift by 4 (36 & 0x1F = 4)
    li t0, 16
    li t1, 36
    srl t2, t0, t1        # t2 = 16 >> 4 = 1
    li t3, 1
    bne t2, t3, fail
    
    # All passed
    li a7, 64
    li a0, 1
    la a1, pass_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 0
    ecall

fail:
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
    .ascii "PASS\n"
fail_msg:
    .ascii "FAIL\n"
