# Program that writes to framebuffer immediately on startup
# Tests that memory-mapped I/O at 0x20000 is accessible

.section .text
.globl _start

_start:
    li t0, 0x20000      # framebuffer base address
    li t1, 0xFF
    sb t1, 0(t0)        # write one pixel
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
