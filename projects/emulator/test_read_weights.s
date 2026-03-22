.section .text
.globl _start

_start:
    # Load address of embedded data
    la t0, model_data
    
    # Read weights (should be at offset 60 from start)
    li t1, 60  # offset of weights
    add t1, t0, t1
    flw fa0, 0(t1)
    
    # Convert to integer for exit code
    fcvt.wu.s a0, fa0
    
    # Exit
    li a7, 93
    ecall

.section .data
.align 4
model_data:
    .incbin "test_safe.bin"
