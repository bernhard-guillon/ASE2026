# Test FEQ.S instruction
# Directly test floating-point equality comparison

.section .text
.globl _start

_start:
    # Load two floats
    li x10, 0x3f800000  # 1.0
    fmv.w.x f1, x10
    
    li x10, 0x3f800000  # 1.0
    fmv.w.x f2, x10
    
    # Compare: f1 == f2, result goes to x11
    feq.s x11, f1, f2   # x11 should be 1 if equal
    
    # Check result
    addi x10, x11, 48   # Convert to ASCII
    li x11, 1           # fd = stdout
    li x12, 64          # write syscall
    addi sp, sp, -1
    sb x10, 0(sp)
    mv x10, sp
    li x12, 1           # length
    ecall
    
    # Print newline
    li x10, 10          # newline
    addi x10, x10, 48
    addi sp, sp, -1
    sb x10, 0(sp)
    mv x10, sp
    li x11, 1
    li x12, 64
    li x12, 1
    ecall
    
    # Exit
    li x10, 93
    li x11, 0
    ecall
