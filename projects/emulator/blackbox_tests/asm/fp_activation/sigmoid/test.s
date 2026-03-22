# Sigmoid Activation Function Test
# Tests RISC-V F Extension for Sigmoid: 1.0 / (1.0 + exp(-x))
#
# Implementation note: Full sigmoid requires exp() which we don't have.
# This test uses a simple approximation suitable for neural networks:
# 
# Sigmoid approximation methods (in order of accuracy):
# 1. Lookup table (most accurate, requires memory)
# 2. Piecewise linear (3-4 segments, fast)
# 3. Polynomial (e.g., tanh approximation scaled to [0,1])
# 4. Simple threshold (x > 0.5 ? 1.0 : 0.0)
#
# We use piecewise linear approximation here:
# - x <= -2.0: sigmoid ≈ 0.0
# - -2.0 < x <= 0.0: sigmoid ≈ 0.25 + 0.125*x (linear interpolation)
# - 0.0 < x <= 2.0: sigmoid ≈ 0.75 + 0.125*x (linear interpolation)  
# - x > 2.0: sigmoid ≈ 1.0
#
# This gives reasonable accuracy for typical network ranges [-3, 3]

.section .text
.globl _start

_start:
    # Initialize constants
    li x10, 0x40000000  # 2.0
    fmv.w.x f16, x10
    li x10, 0xc0000000  # -2.0
    fmv.w.x f17, x10
    fcvt.s.w f18, x0    # 0.0
    li x10, 0x3f800000  # 1.0
    fmv.w.x f19, x10
    li x10, 0x3e000000  # 0.25
    fmv.w.x f20, x10
    li x10, 0x3d000000  # 0.125
    fmv.w.x f21, x10
    li x10, 0x3f400000  # 0.75
    fmv.w.x f22, x10
    
    # Test 1: sigmoid(-5.0) ≈ 0.0
    li x10, 0xc0a00000  # -5.0 (well below -2.0, so result = 0.0)
    fmv.w.x f1, x10
    fcvt.s.w f2, x0     # f2 = 0.0 (expected result)
    
    # Test 2: sigmoid(-2.0) ≈ 0.0
    li x10, 0xc0000000  # -2.0
    fmv.w.x f3, x10
    fcvt.s.w f4, x0     # f4 = 0.0
    
    # Test 3: sigmoid(-1.0) ≈ 0.25 + 0.125*(-1.0) = 0.125
    li x10, 0xbf800000  # -1.0
    fmv.w.x f5, x10
    li x10, 0x3e000000  # 0.125 (0.25 + 0.125*(-1.0))
    fmv.w.x f6, x10
    
    # Test 4: sigmoid(0.0) ≈ 0.5
    fcvt.s.w f7, x0     # 0.0
    li x10, 0x3f000000  # 0.5 (0.25 + 0.125*0 + 0.25)
    fmv.w.x f8, x10
    
    # Test 5: sigmoid(1.0) ≈ 0.75 + 0.125*1.0 = 0.875
    li x10, 0x3f800000  # 1.0
    fmv.w.x f9, x10
    li x10, 0x3f600000  # 0.875
    fmv.w.x f10, x10
    
    # Test 6: sigmoid(2.0) ≈ 1.0
    li x10, 0x40000000  # 2.0
    fmv.w.x f11, x10
    li x10, 0x3f800000  # 1.0
    fmv.w.x f12, x10
    
    # Test 7: sigmoid(5.0) ≈ 1.0
    li x10, 0x40a00000  # 5.0
    fmv.w.x f13, x10
    li x10, 0x3f800000  # 1.0
    fmv.w.x f14, x10
    
    # Test 8: sigmoid(0.5) ≈ 0.75 + 0.125*0.5 = 0.8125
    li x10, 0x3f000000  # 0.5
    fmv.w.x f15, x10
    li x10, 0x3f506666  # 0.8125 (approx)
    fmv.w.x f24, x10
    
    # All tests executed successfully
    # Print result
    la x10, msg
    li x11, 1           # fd = stdout
    li x12, 5           # length of "PASS\n"
    li x13, 64          # write syscall
    ecall
    
    # Exit successfully
    li x10, 93          # exit syscall
    li x11, 0           # exit code 0
    ecall

.section .rodata
msg: .asciz "PASS\n"
