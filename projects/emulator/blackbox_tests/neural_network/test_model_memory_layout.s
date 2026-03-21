# Test - Verify neural network model weights at correct memory locations

.globl _start

_start:
    # Initialize pass counter in s0
    ori s0, zero, 0

    # Test 1 - Generator model magic at 0x10000
    lui a0, 0x10
    lw a1, 0(a0)
    lui a2, 0x4e524
    ori a2, a2, 0x14e
    bne a1, a2, skip_test1
    addi s0, s0, 1
skip_test1:
    
    # Test 2 - Generator version at 0x10004
    lui a0, 0x10
    addi a0, a0, 4
    lw a1, 0(a0)
    ori a2, zero, 1
    bne a1, a2, skip_test2
    addi s0, s0, 1
skip_test2:

    # Test 3 - Generator layers at 0x1000C
    lui a0, 0x10
    addi a0, a0, 12
    lw a1, 0(a0)
    ori a2, zero, 3
    bne a1, a2, skip_test3
    addi s0, s0, 1
skip_test3:

    # Test 4 - First weight at 0x10080
    lui a0, 0x10
    addi a0, a0, 128
    lw a1, 0(a0)
    beq a1, zero, skip_test4
    addi s0, s0, 1
skip_test4:

    # Test 5 - First bias at 0xF3C80
    lui a0, 0xf4
    addi a0, a0, -896
    lw a1, 0(a0)
    beq a1, zero, skip_test5
    addi s0, s0, 1
skip_test5:

    # Test 6 - Recognizer magic at 0xF4ABC
    lui a0, 0xf5
    addi a0, a0, -1348
    lw a1, 0(a0)
    lui a2, 0x4e524
    ori a2, a2, 0x14e
    bne a1, a2, skip_test6
    addi s0, s0, 1
skip_test6:

    # Test 7 - Recognizer version at 0xF4AC0
    lui a0, 0xf5
    addi a0, a0, -1344
    lw a1, 0(a0)
    ori a2, zero, 1
    bne a1, a2, done
    addi s0, s0, 1

done:
    # Exit with pass count
    ori a0, s0, 0
    ori a7, zero, 93
    ecall
