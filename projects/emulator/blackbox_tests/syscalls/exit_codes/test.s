# Exit Codes Test
# Tests that exit syscall properly sets exit code

.section .text
.globl _start

_start:
    # Exit with code 42
    li a7, 93
    li a0, 42
    ecall
    
    # Should not reach here
    li a7, 93
    li a0, 1
    ecall
