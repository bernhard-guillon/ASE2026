# LUI Test
# Tests LUI (load upper immediate)

.section .text
.globl _start

_start:
    # Load 0x12345 into upper 20 bits: should give 0x12345000
    lui t0, 0x12345
    li t1, 0x12345000
    bne t0, t1, fail
    
    # LUI 0 should give 0
    lui t0, 0
    li t1, 0
    bne t0, t1, fail
    
    # LUI 1 should give 0x1000
    lui t0, 1
    li t1, 0x1000
    bne t0, t1, fail
    
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
