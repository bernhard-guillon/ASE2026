# Signed Load Test
# Tests LB, LH with sign extension

.section .text
.globl _start

_start:
    # Test LB sign extension: load 0xFF should give -1
    la t0, byte_neg
    lb t1, 0(t0)          # t1 = -1 (sign extended from 0xFF)
    li t2, -1
    bne t1, t2, fail
    
    # Test LB zero extension reference: 0x7F should be 127
    la t0, byte_pos
    lb t1, 0(t0)          # t1 = 127
    li t2, 127
    bne t1, t2, fail
    
    # Test LBU unsigned: 0xFF should be 255
    la t0, byte_neg
    lbu t1, 0(t0)         # t1 = 255 (unsigned)
    li t2, 255
    bne t1, t2, fail
    
    # Test LH sign extension: 0xFFFF should be -1
    la t0, half_neg
    lh t1, 0(t0)          # t1 = -1
    li t2, -1
    bne t1, t2, fail
    
    # Test LHU unsigned: 0xFFFF should be 65535
    la t0, half_neg
    lhu t1, 0(t0)         # t1 = 65535
    li t2, 65535
    bne t1, t2, fail
    
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
byte_neg:
    .byte 0xFF
byte_pos:
    .byte 0x7F
half_neg:
    .half 0xFFFF
pass_msg:
    .ascii "PASS\n"
fail_msg:
    .ascii "FAIL\n"
