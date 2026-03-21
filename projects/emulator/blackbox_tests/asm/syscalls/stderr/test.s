# Stderr Write Test
# Tests writing to stderr (fd=2)

.section .text
.globl _start

_start:
    # Write "ERR\n" to stderr (fd=2)
    li a7, 64
    li a0, 2               # fd = 2 (stderr)
    la a1, err_msg
    li a2, 4
    ecall
    
    # Also write to stdout
    li a7, 64
    li a0, 1               # fd = 1 (stdout)
    la a1, pass_msg
    li a2, 5
    ecall
    
    # Exit success
    li a7, 93
    li a0, 0
    ecall

.section .data
err_msg:
    .ascii "ERR\n"
pass_msg:
    .ascii "PASS\n"
