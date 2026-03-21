# JALR Test
# Tests JALR (jump and link register) instruction

.section .text
.globl _start

_start:
    # Load address of target into t0
    la t0, target
    # Jump to target, saving PC+4 in ra
    jalr ra, 0(t0)
    # Should not reach here
    j fail

target:
    # JALR worked if we're here
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
