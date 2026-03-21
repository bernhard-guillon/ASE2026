# Program with a constant bit pattern in .rodata
# Tests loading and reading a fixed byte pattern

.section .rodata
.align 2
pattern:
    .byte 0xAA, 0x55, 0xAA, 0x55
    .byte 0xFF, 0x00, 0xFF, 0x00

.section .text
.globl _start

_start:
    la t0, pattern
    lb t1, 0(t0)        # load 0xAA
    lb t2, 1(t0)        # load 0x55
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
