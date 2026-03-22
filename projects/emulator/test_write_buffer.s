.section .text
.globl _start

_start:
    # Allocate input buffer on stack
    # sp starts at 0x80000000, so we use 0x1000 (after ELF)
    li t0, 0x1000
    
    # Write a value to the buffer
    li t1, 42
    sw t1, 0(t0)
    
    # Read it back
    lw a0, 0(t0)
    
    # Exit with the value
    li a7, 93
    ecall

.section .data
.align 4
model_data:
    .incbin "test_safe.bin"
