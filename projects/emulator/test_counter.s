.section .text
.globl _start

_start:
    li sp, 0xF000
    li t0, 0               # counter
    li t1, 5               # max iterations
    
loop:
    # Do some work (simplified from neural network)
    la s0, model_data
    lw a0, 0(s0)           # read magic
    
    addi t0, t0, 1
    blt t0, t1, loop
    
    # Exit with counter
    mv a0, t0
    li a7, 93
    ecall

.section .data
model_data:
    .incbin "test_safe.bin"
