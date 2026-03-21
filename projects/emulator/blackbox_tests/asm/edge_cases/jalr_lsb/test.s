# JALR LSB Clearing Test
# Tests that JALR clears the LSB of the target address

.section .text
.globl _start

_start:
    # Load odd address into t0 (should be cleared)
    la t0, target
    ori t0, t0, 1         # Set LSB to 1 (now target is odd)
    
    # JALR should clear the LSB and jump correctly
    jalr ra, 0(t0)
    
    # Should not reach here
    j fail

target:
    # JALR worked if we're here (LSB was properly cleared)
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
