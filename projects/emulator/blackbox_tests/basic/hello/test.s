# Hello World Test
# Tests basic syscall functionality (write to stdout and exit)

.section .text
.globl _start

_start:
    # Write "Hello, World!\n" to stdout
    li a7, 64              # syscall number for write (64)
    li a0, 1               # file descriptor 1 = stdout
    la a1, hello_msg       # buffer address
    li a2, 14              # count (length of string including \n)
    ecall

    # Exit with status 0
    li a7, 93              # syscall number for exit (93)
    li a0, 0               # exit status = 0 (success)
    ecall

.section .data
hello_msg:
    .string "Hello, World!\n"
