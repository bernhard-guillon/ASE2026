# Signed Comparisons Test
# Tests SLT with various signed values

.section .text
.globl _start

_start:
    # Test SLT positive < positive: 5 < 10
    li t0, 5
    li t1, 10
    slt t2, t0, t1        # t2 = 1
    li t3, 1
    bne t2, t3, fail
    
    # Test SLT positive > positive: 10 < 5
    li t0, 10
    li t1, 5
    slt t2, t0, t1        # t2 = 0
    li t3, 0
    bne t2, t3, fail
    
    # Test SLT negative < positive: -5 < 10
    li t0, -5
    li t1, 10
    slt t2, t0, t1        # t2 = 1 (signed)
    li t3, 1
    bne t2, t3, fail
    
    # Test SLT negative < negative: -10 < -5
    li t0, -10
    li t1, -5
    slt t2, t0, t1        # t2 = 1
    li t3, 1
    bne t2, t3, fail
    
    # Test SLTU unsigned: (unsigned)5 < (unsigned)10
    li t0, 5
    li t1, 10
    sltu t2, t0, t1       # t2 = 1
    li t3, 1
    bne t2, t3, fail
    
    # Test SLTU with large unsigned: 0xFFFFFFFF < 0x00000001
    # In unsigned: large value is NOT less than 1
    li t0, -1             # 0xFFFFFFFF
    li t1, 1
    sltu t2, t0, t1       # t2 = 0 (unsigned comparison)
    li t3, 0
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
