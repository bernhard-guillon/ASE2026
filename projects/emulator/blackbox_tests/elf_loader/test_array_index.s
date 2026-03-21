# Program that indexes into an array in .rodata
# Tests that array access through pointer arithmetic works

.section .rodata
.align 2
array:
    .word 10, 20, 30, 40, 50

.section .text
.globl _start

_start:
    la t0, array
    li t1, 2            # index 2
    slli t1, t1, 2      # multiply by 4 (word size)
    add t0, t0, t1
    lw t2, 0(t0)        # load array[2] = 30
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
