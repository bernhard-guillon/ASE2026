# Memory Operations Test
# Tests LW (load word), SW (store word), and data section access

.section .text
.globl _start

_start:
    # Load word from data section
    la t0, test_value      # Load address of test_value
    lw t1, 0(t0)           # Load word from address
    # t1 should be 0x12345678
    
    li t2, 0x12345678
    bne t1, t2, fail
    
    # Store word to data section
    la t0, result_value
    li t1, 0xDEADBEEF
    sw t1, 0(t0)           # Store word to address
    
    # Load it back and verify
    lw t2, 0(t0)
    bne t1, t2, fail
    
    # Test byte operations
    la t0, byte_array
    lb t1, 0(t0)           # Load first byte (0x41 = 'A')
    li t2, 0x41
    bne t1, t2, fail
    
    # Test halfword operations
    la t0, half_value
    lh t1, 0(t0)           # Load halfword (0x1234)
    li t2, 0x1234
    bne t1, t2, fail
    
    # All tests passed
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
test_value:
    .word 0x12345678
result_value:
    .word 0x00000000
byte_array:
    .byte 0x41, 0x42, 0x43, 0x44  # "ABCD"
half_value:
    .half 0x1234
pass_msg:
    .string "PASS\n"
fail_msg:
    .string "FAIL\n"
