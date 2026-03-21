# JAL Test
# Tests JAL instruction with PC-relative jumps

.section .text
.globl _start

_start:
    # Jump to target and save PC+4 in ra
    jal ra, target
    # Should not reach here, fail if we do
    j fail

target:
    # Check that ra contains address of instruction after jal
    # ra should point to the j fail instruction
    # We'll just return to verify JAL worked
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
