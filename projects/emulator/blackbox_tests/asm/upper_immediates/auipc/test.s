# AUIPC Test
# Tests AUIPC (add upper immediate to PC)

.section .text
.globl _start

_start:
    # AUIPC should add upper immediate to current PC
    # At _start, PC is 0, so AUIPC 0, x0 should give 0 in x0
    auipc t0, 0           # t0 = PC + 0 = PC (should be 0 or 4 depending on alignment)
    # Since PC is 0 at start, t0 should be 0
    li t1, 0
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
