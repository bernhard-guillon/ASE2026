# Multiple Writes Test
# Tests multiple write syscalls in sequence

.section .text
.globl _start

_start:
    # Write "A"
    li a7, 64
    li a0, 1
    la a1, msg_a
    li a2, 1
    ecall
    
    # Write "B"
    li a7, 64
    li a0, 1
    la a1, msg_b
    li a2, 1
    ecall
    
    # Write "C\n"
    li a7, 64
    li a0, 1
    la a1, msg_c
    li a2, 2
    ecall
    
    # Exit success
    li a7, 93
    li a0, 0
    ecall

.section .data
msg_a:
    .ascii "A"
msg_b:
    .ascii "B"
msg_c:
    .ascii "C\n"
