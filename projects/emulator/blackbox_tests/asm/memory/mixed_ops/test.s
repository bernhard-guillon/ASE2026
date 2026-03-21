# Mixed Load/Store Operations
# Tests various combinations of load/store with different sizes

.section .text
.globl _start

_start:
    # Store word, load as bytes
    li t0, 0x12345678
    la t1, test_data
    sw t0, 0(t1)
    
    # Load high byte
    lb t2, 3(t1)          # Load 0x12 sign-extended
    li t3, 0x12
    bne t2, t3, fail
    
    # Load low byte
    lb t2, 0(t1)          # Load 0x78 sign-extended (as signed = 0x78 = 120)
    li t3, 0x78
    bne t2, t3, fail
    
    # Load as unsigned byte
    lbu t2, 3(t1)         # Load 0x12 unsigned
    li t3, 0x12
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
test_data:
    .word 0x00000000
pass_msg:
    .ascii "PASS\n"
fail_msg:
    .ascii "FAIL\n"
