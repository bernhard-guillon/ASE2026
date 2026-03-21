# Fibonacci Test
# Calculates the 10th Fibonacci number and prints result
# fib(10) = 55

.section .text
.globl _start

_start:
    li a0, 10              # Calculate fib(10)
    jal ra, fibonacci
    # Result is in a0
    
    # a0 should be 55
    li t0, 55
    bne a0, t0, fail
    
    # Print "fib(10)=55\n"
    li a7, 64
    li a0, 1
    la a1, result_msg
    li a2, 12
    ecall
    
    # Exit success
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

# Fibonacci function
# Input: a0 = n
# Output: a0 = fib(n)
# Uses iterative approach
fibonacci:
    # Handle base cases
    li t0, 0
    beq a0, t0, fib_return  # fib(0) = 0
    
    li t0, 1
    beq a0, t0, fib_return  # fib(1) = 1
    
    # Iterative calculation
    li t1, 0               # prev = 0
    li t2, 1               # curr = 1
    li t3, 2               # i = 2
    
fib_loop:
    bgt t3, a0, fib_done   # if i > n, done
    
    add t4, t1, t2         # next = prev + curr
    mv t1, t2              # prev = curr
    mv t4, t2              # curr = next
    addi t3, t3, 1         # i++
    j fib_loop

fib_done:
    mv a0, t2              # return curr
    
fib_return:
    ret

.section .data
result_msg:
    .string "fib(10)=55\n"
fail_msg:
    .string "FAIL\n"
