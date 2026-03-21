# Different Width Load/Store Test
# Tests SH, SB to ensure proper truncation

.section .text
.globl _start

_start:
    # Test SB: store 0x12345678 but only lower byte goes
    li t0, 0x12345678
    la t1, store_result
    sb t0, 0(t1)          # store lower byte (0x78)
    lb t2, 0(t1)          # load back
    li t3, 0x78
    bne t2, t3, fail
    
    # Test SH: store 0x12345678 but only lower halfword goes
    li t0, 0x12345678
    la t1, store_result
    sh t0, 0(t1)          # store lower halfword (0x5678)
    lh t2, 0(t1)          # load back
    li t3, 0x5678
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
store_result:
    .word 0x00000000
pass_msg:
    .ascii "PASS\n"
fail_msg:
    .ascii "FAIL\n"
