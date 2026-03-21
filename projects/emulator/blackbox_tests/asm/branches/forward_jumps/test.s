# Forward Jump Test
# Tests forward branches with large offsets

.section .text
.globl _start

_start:
    # Jump forward over some code
    beq zero, zero, skip_code
    
    # This section should be skipped
    li t0, 999
    li t1, 999
    
skip_code:
    # We should arrive here
    li a7, 64
    li a0, 1
    la a1, pass_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 0
    ecall

.section .data
pass_msg:
    .ascii "PASS\n"
