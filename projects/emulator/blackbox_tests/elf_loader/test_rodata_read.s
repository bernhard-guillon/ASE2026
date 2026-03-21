# Program with .rodata section
# Tests that ELF loader correctly loads read-only data segments

.section .rodata
.align 2
const_values:
    .word 42
    .word 99
    .word 255

.section .text
.globl _start

_start:
    la t0, const_values
    lw t1, 0(t0)        # load 42
    lw t2, 4(t0)        # load 99
    lw t3, 8(t0)        # load 255
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
