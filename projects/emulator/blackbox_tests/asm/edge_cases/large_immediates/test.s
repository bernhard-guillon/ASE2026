# Large Immediate Values Test
# Tests handling of large immediate constants

.section .text
.globl _start

_start:
    # Load large negative immediate
    li t0, -2048          # Minimum 12-bit signed immediate
    li t1, -2048
    bne t0, t1, fail
    
    # Load large positive immediate
    li t0, 2047           # Maximum 12-bit signed immediate
    li t1, 2047
    bne t0, t1, fail
    
    # Very large constant (requires lui + addi)
    li t0, 0x12345678
    li t1, 0x12345678
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
