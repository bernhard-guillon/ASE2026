# Loop and Function Call Test
# Tests loops and function returns
# Simple countdown function

.section .text
.globl _start

_start:
    li a0, 5               # Start countdown from 5
    jal ra, countdown
    
    # If we got here, the function returned correctly
    # Print "PASS\n"
    li a7, 64
    li a0, 1
    la a1, result_msg
    li a2, 5
    ecall
    
    # Exit success
    li a7, 93
    li a0, 0
    ecall

# Countdown function - counts down from n to 0
countdown:
    beq a0, zero, count_done
    addi a0, a0, -1
    jal zero, countdown   # Tail call (doesn't need ra)
    
count_done:
    ret

.section .data
result_msg:
    .ascii "PASS\n"
