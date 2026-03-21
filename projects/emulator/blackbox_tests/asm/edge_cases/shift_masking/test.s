# Shift Amount Masking Test
# Tests that shift amounts are masked to 5 bits (only lower 5 bits used)

.section .text
.globl _start

_start:
    # Shift by 4 should be same as shift by 36 (36 & 0x1F = 4)
    li t0, 16
    li t1, 4
    sll t2, t0, t1        # t2 = 16 << 4 = 256
    
    li t0, 16
    li t1, 36             # 36 & 0x1F = 4
    sll t3, t0, t1        # t3 = 16 << 4 = 256
    
    bne t2, t3, fail
    
    # SRL also masks: 1024 >> 5 = 32, 1024 >> 37 = 32
    li t0, 1024
    li t1, 5
    srl t2, t0, t1        # t2 = 1024 >> 5 = 32
    
    li t0, 1024
    li t1, 37             # 37 & 0x1F = 5
    srl t3, t0, t1        # t3 = 1024 >> 5 = 32
    
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
