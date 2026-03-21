# x0 Register Immutability Test
# Tests that x0 (zero register) cannot be written to

.section .text
.globl _start

_start:
    # Try to write to x0 via ADD
    li t0, 100
    li t1, 50
    add x0, t0, t1        # x0 = t0 + t1, but should be ignored
    
    # x0 should still be 0
    li t2, 0
    bne x0, t2, fail
    
    # Try to write via ADDI
    addi x0, x0, 999      # x0 += 999, but should remain 0
    bne x0, t2, fail
    
    # Try JAL - should not write to x0
    jal x0, skip_target
    j fail                # Should jump over this

skip_target:
    # x0 should still be 0
    bne x0, t2, fail
    
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
