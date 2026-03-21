# Program with .rodata section
# Tests that ELF loader correctly loads read-only data segments
# The combined size of .text + .rodata must exceed 100 bytes for the RodataSegment test.

.section .rodata
.align 2
const_values:
    .word 42
    .word 99
    .word 255
# Additional data to ensure total segment size exceeds 100 bytes
padding_data:
    .word 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    .word 11, 12, 13, 14, 15, 16, 17, 18, 19, 20

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
