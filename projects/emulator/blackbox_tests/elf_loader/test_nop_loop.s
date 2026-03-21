# Simple NOP program that exits cleanly
# Used to test ELF loading with a minimal program

.section .text
.globl _start

_start:
    nop
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
