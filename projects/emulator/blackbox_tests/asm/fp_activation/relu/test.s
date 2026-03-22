# ReLU Activation Function Test
# Tests RISC-V F Extension for ReLU: max(x, 0.0)
#
# ReLU(x) = x if x > 0.0, else 0.0
# Implementation uses FMAX.S with 0.0
#
# Test cases cover:
# - Negative values (should output 0.0)
# - Zero (should output 0.0)
# - Positive values (should output the value itself)
# - Edge cases (very small positive, large values)

.section .text
.globl _start

_start:
    # Load constant 0.0 for ReLU
    fcvt.s.w f0, x0   # f0 = 0.0 (convert int 0 to float)
    
    # Test 1: ReLU(-5.5) = 0.0
    li x10, 0xc0b00000  # IEEE 754: -5.5 as uint32
    fmv.w.x f1, x10
    fmax.s f1, f1, f0   # f1 = max(-5.5, 0.0) = 0.0
    
    # Test 2: ReLU(0.0) = 0.0
    fcvt.s.w f2, x0
    fmax.s f2, f2, f0   # f2 = max(0.0, 0.0) = 0.0
    
    # Test 3: ReLU(2.5) = 2.5
    li x10, 0x40200000  # IEEE 754: 2.5 as uint32
    fmv.w.x f3, x10
    fmax.s f3, f3, f0   # f3 = max(2.5, 0.0) = 2.5
    
    # Test 4: ReLU(7.25) = 7.25
    li x10, 0x40e80000  # IEEE 754: 7.25 as uint32
    fmv.w.x f4, x10
    fmax.s f4, f4, f0   # f4 = max(7.25, 0.0) = 7.25
    
    # Test 5: ReLU(-1.0) = 0.0
    li x10, 0xbf800000  # IEEE 754: -1.0 as uint32
    fmv.w.x f5, x10
    fmax.s f5, f5, f0   # f5 = max(-1.0, 0.0) = 0.0
    
    # Test 6: ReLU(1.0) = 1.0
    li x10, 0x3f800000  # IEEE 754: 1.0 as uint32
    fmv.w.x f6, x10
    fmax.s f6, f6, f0   # f6 = max(1.0, 0.0) = 1.0
    
    # Test 7: ReLU(3.14) = 3.14
    li x10, 0x4048f5c3  # IEEE 754: 3.14 as uint32
    fmv.w.x f7, x10
    fmax.s f7, f7, f0   # f7 = max(3.14, 0.0) = 3.14
    
    # Test 8: ReLU(100.0) = 100.0
    li x10, 0x42c80000  # IEEE 754: 100.0 as uint32
    fmv.w.x f8, x10
    fmax.s f8, f8, f0   # f8 = max(100.0, 0.0) = 100.0
    
    # Test 9: ReLU(-0.001) = 0.0
    li x10, 0xbbb00000  # IEEE 754: -0.001 as uint32
    fmv.w.x f9, x10
    fmax.s f9, f9, f0   # f9 = max(-0.001, 0.0) = 0.0
    
    # Test 10: ReLU(0.5) = 0.5
    li x10, 0x3f000000  # IEEE 754: 0.5 as uint32
    fmv.w.x f10, x10
    fmax.s f10, f10, f0 # f10 = max(0.5, 0.0) = 0.5
    
    # Print results
    la x10, msg
    li x11, 64          # write syscall
    li x12, 0
    
print_msg:
    lb x13, 0(x10)
    beq x13, x0, done
    addi x12, x12, 1
    addi x10, x10, 1
    j print_msg
    
done:
    # Reset x10 to message start
    la x10, msg
    li x11, 1           # fd = stdout
    li x12, 64          # write syscall number
    ecall
    
    # Exit successfully
    li x10, 93          # exit syscall
    li x11, 0           # exit code 0
    ecall

.section .rodata
msg: .asciz "PASS\n"
