# Loop Test
# Tests iterative looping with branches

.section .text
.globl _start

_start:
    # Loop 10 times, accumulating sum
    li t0, 0              # sum = 0
    li t1, 0              # i = 0
    li t2, 10             # limit = 10

loop:
    beq t1, t2, loop_done # if i == 10, done
    add t0, t0, t1        # sum += i
    addi t1, t1, 1        # i++
    j loop

loop_done:
    # sum should be 0+1+2+...+9 = 45
    li t3, 45
    bne t0, t3, fail
    
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
