# Program that reads data at a fixed offset from a .rodata base
# Tests offset addressing in read-only data

.section .rodata
.align 2
data_block:
    .byte 1, 2, 3, 4, 5, 6, 7, 8

.section .text
.globl _start

_start:
    la t0, data_block
    lb t1, 0(t0)        # read byte at offset 0 -> 1
    lb t2, 4(t0)        # read byte at offset 4 -> 5
    lb t3, 7(t0)        # read byte at offset 7 -> 8
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
