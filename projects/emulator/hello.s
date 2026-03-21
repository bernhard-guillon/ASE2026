# RV32I Hello World Assembly
# This program writes "Hello, World!\n" to stdout and exits

.section .text
.globl _start

_start:
    # write(1, message, 14)
    li a0, 1            # stdout file descriptor
    la a1, message      # load address of message
    li a2, 14           # length of message
    li a7, 64           # write syscall number
    ecall               # invoke syscall
    
    # exit(0)
    li a0, 0            # exit code
    li a7, 93           # exit syscall number
    ecall               # invoke syscall

.section .data
message:
    .string "Hello, World!\n"
