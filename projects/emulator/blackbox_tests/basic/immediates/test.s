# Immediate Operations Test
# Tests ADDI, ANDI, ORI, XORI, SLTI, SLTIU

.section .text
.globl _start

_start:
    # Test ADDI
    li t0, 100
    addi t0, t0, 50       # t0 = 150
    li t1, 150
    bne t0, t1, fail
    
    # Test ANDI
    li t0, 0xFF
    andi t0, t0, 0xF0     # t0 = 0xF0
    li t1, 0xF0
    bne t0, t1, fail
    
    # Test ORI
    li t0, 0x0F
    ori t0, t0, 0xF0      # t0 = 0xFF
    li t1, 0xFF
    bne t0, t1, fail
    
    # Test XORI
    li t0, 0xAA
    xori t0, t0, 0xFF     # t0 = 0x55
    li t1, 0x55
    bne t0, t1, fail
    
    # Test SLTI
    li t0, 10
    slti t0, t0, 20       # t0 = 1 (10 < 20)
    li t1, 1
    bne t0, t1, fail
    
    # Test SLTIU
    li t0, 10
    sltiu t0, t0, 20      # t0 = 1 (10 < 20 unsigned)
    li t1, 1
    bne t0, t1, fail
    
    # All passed
    li a7, 64
    li a0, 1
    la a1, pass_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 0
    ecall

fail:
    li a7, 64
    li a0, 1
    la a1, fail_msg
    li a2, 5
    ecall
    
    li a7, 93
    li a0, 1
    ecall

.section .data
pass_msg:
    .ascii "PASS\n"
fail_msg:
    .ascii "FAIL\n"
