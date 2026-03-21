# Negative Branch Offsets Test
# Tests backward branches

.section .text
.globl _start

_start:
    li t0, 5              # Counter

loop:
    addi t0, t0, -1       # Decrement
    bne t0, zero, loop    # Jump backward if not zero
    
    # Loop complete
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
