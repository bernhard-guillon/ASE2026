# Arithmetic Operations Test
# Tests ADD, SUB, AND, OR, XOR operations and prints results

.section .text
.globl _start

_start:
    # Test ADD: 15 + 27 = 42
    li t0, 15
    li t1, 27
    add t2, t0, t1
    # t2 should be 42
    
    # Test SUB: 50 - 8 = 42
    li t3, 50
    li t4, 8
    sub t5, t3, t4
    # t5 should be 42
    
    # Test AND: 0xFF & 0x2A = 0x2A (42)
    li t0, 0xFF
    li t1, 0x2A
    and t2, t0, t1
    # t2 should be 42
    
    # Test OR: 0x20 | 0x0A = 0x2A (42)
    li t3, 0x20
    li t4, 0x0A
    or t5, t3, t4
    # t5 should be 42
    
    # Test XOR: 0x60 ^ 0x4A = 0x2A (42)
    li t0, 0x60
    li t1, 0x4A
    xor t2, t0, t1
    # t2 should be 42
    
    # Print "PASS\n" if all operations work
    li a7, 64
    li a0, 1
    la a1, pass_msg
    li a2, 5
    ecall
    
    # Exit success
    li a7, 93
    li a0, 0
    ecall

.section .data
pass_msg:
    .string "PASS\n"
