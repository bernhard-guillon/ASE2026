# Floating-Point Extension (F) Blackbox Test
# Tests basic FP instructions using actual RISC-V assembler
# This ensures our implementation is standard-compliant

.section .text
.globl _start

_start:
    # Test 1: FLW and FSW
    # Load π from memory and store back
    la      t0, pi_value
    flw     f1, 0(t0)           # Load π into f1
    la      t1, result1
    fsw     f1, 0(t1)           # Store back to verify
    
    # Test 2: FADD.S
    # Add 2.5 + 3.5 = 6.0
    la      t0, val_2_5
    flw     f2, 0(t0)
    la      t0, val_3_5
    flw     f3, 0(t0)
    fadd.s  f4, f2, f3          # f4 = 2.5 + 3.5
    la      t1, result2
    fsw     f4, 0(t1)
    
    # Test 3: FSUB.S
    # Subtract 10.0 - 3.5 = 6.5
    la      t0, val_10_0
    flw     f5, 0(t0)
    la      t0, val_3_5
    flw     f6, 0(t0)
    fsub.s  f7, f5, f6          # f7 = 10.0 - 3.5
    la      t1, result3
    fsw     f7, 0(t1)
    
    # Test 4: FMUL.S
    # Multiply 2.0 * 3.5 = 7.0
    la      t0, val_2_0
    flw     f8, 0(t0)
    la      t0, val_3_5
    flw     f9, 0(t0)
    fmul.s  f10, f8, f9         # f10 = 2.0 * 3.5
    la      t1, result4
    fsw     f10, 0(t1)
    
    # Test 5: FMAX.S (ReLU pattern)
    # max(-5.5, 0.0) = 0.0
    la      t0, val_neg_5_5
    flw     f11, 0(t0)
    la      t0, val_0_0
    flw     f12, 0(t0)
    fmax.s  f13, f11, f12       # f13 = max(-5.5, 0.0)
    la      t1, result5
    fsw     f13, 0(t1)
    
    # Test 6: FMAX.S with positive
    # max(7.25, 0.0) = 7.25
    la      t0, val_7_25
    flw     f14, 0(t0)
    la      t0, val_0_0
    flw     f15, 0(t0)
    fmax.s  f16, f14, f15       # f16 = max(7.25, 0.0)
    la      t1, result6
    fsw     f16, 0(t1)
    
    # Test 7: FCVT.S.W (int to float)
    # Convert 42 to 42.0
    li      t0, 42
    fcvt.s.w f17, t0            # f17 = float(42)
    la      t1, result7
    fsw     f17, 0(t1)
    
    # Test 8: FMV.W.X and FMV.X.W
    # Move bits between integer and FP registers
    la      t0, pi_value
    lw      t2, 0(t0)           # Load π bits into t2
    fmv.w.x f18, t2             # Move to FP register
    fmv.x.w t3, f18             # Move back to integer
    la      t1, result8
    sw      t3, 0(t1)           # Store result (should match π)
    
    # Test 9: Matrix multiply accumulation pattern
    # result = 0.5 * 1.0 + 1.5 * 2.0 + 2.5 (bias)
    #        = 0.5 + 3.0 + 2.5 = 6.0
    la      t0, val_2_5
    flw     f20, 0(t0)          # f20 = 2.5 (accumulator/bias)
    la      t0, val_0_5
    flw     f21, 0(t0)          # f21 = 0.5 (weight1)
    la      t0, val_1_0
    flw     f22, 0(t0)          # f22 = 1.0 (input1)
    la      t0, val_1_5
    flw     f23, 0(t0)          # f23 = 1.5 (weight2)
    la      t0, val_2_0
    flw     f24, 0(t0)          # f24 = 2.0 (input2)
    
    fmul.s  f25, f21, f22       # f25 = 0.5 * 1.0 = 0.5
    fadd.s  f20, f20, f25       # f20 = 2.5 + 0.5 = 3.0
    fmul.s  f26, f23, f24       # f26 = 1.5 * 2.0 = 3.0
    fadd.s  f20, f20, f26       # f20 = 3.0 + 3.0 = 6.0
    la      t1, result9
    fsw     f20, 0(t1)
    
    # Exit with success
    li      a0, 0
    li      a7, 93              # exit syscall
    ecall

.section .data
.align 2

# Test values (IEEE 754 single precision)
pi_value:       .word 0x40490FDB    # 3.14159265
val_2_5:        .word 0x40200000    # 2.5
val_3_5:        .word 0x40600000    # 3.5
val_10_0:       .word 0x41200000    # 10.0
val_2_0:        .word 0x40000000    # 2.0
val_neg_5_5:    .word 0xC0B00000    # -5.5
val_0_0:        .word 0x00000000    # 0.0
val_7_25:       .word 0x40E80000    # 7.25
val_0_5:        .word 0x3F000000    # 0.5
val_1_0:        .word 0x3F800000    # 1.0
val_1_5:        .word 0x3FC00000    # 1.5

# Results
result1:        .word 0
result2:        .word 0
result3:        .word 0
result4:        .word 0
result5:        .word 0
result6:        .word 0
result7:        .word 0
result8:        .word 0
result9:        .word 0
