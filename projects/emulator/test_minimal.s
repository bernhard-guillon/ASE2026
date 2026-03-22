.section .text
.globl _start

_start:
    # Load address of embedded data
    la t0, model_data
    
    # Read first 4 bytes (magic number)
    lw a0, 0(t0)
    
    # Exit
    li a7, 93
    ecall

.section .data
.align 4
model_data:
    .incbin "test_safe.bin"
