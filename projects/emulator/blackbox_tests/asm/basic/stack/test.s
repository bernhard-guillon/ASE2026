# Stack Operations Test
# Tests using sp and stack for data storage

.section .text
.globl _start

_start:
    # Initialize sp to a safe location (we'll use high memory)
    li sp, 0x10000        # Set sp to 64KB
    
    # Save some values on stack
    addi sp, sp, -12      # Make space for 3 words
    
    li t0, 0x11111111
    sw t0, 0(sp)          # Store at sp+0
    
    li t1, 0x22222222
    sw t1, 4(sp)          # Store at sp+4
    
    li t2, 0x33333333
    sw t2, 8(sp)          # Store at sp+8
    
    # Load them back
    lw t3, 0(sp)          # t3 = 0x11111111
    bne t0, t3, fail
    
    lw t4, 4(sp)          # t4 = 0x22222222
    bne t1, t4, fail
    
    lw t5, 8(sp)          # t5 = 0x33333333
    bne t2, t5, fail
    
    addi sp, sp, 12       # Clean up
    
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
