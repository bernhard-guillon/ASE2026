# Program that fills framebuffer with a constant value
# Tests that writing a sequence of pixels to the framebuffer works

.section .text
.globl _start

_start:
    li t0, 0x20000      # framebuffer base address (FRAMEBUFFER_ADDR)
    li t1, 0x80         # pixel value (128)
    li t2, 400          # total pixels (20x20)
    li t3, 0            # counter
fb_loop:
    sb t1, 0(t0)        # write pixel
    addi t0, t0, 1      # advance pointer
    addi t3, t3, 1      # increment counter
    blt t3, t2, fb_loop # loop until 400 pixels written
    li a7, 93           # exit syscall
    li a0, 0            # exit status 0
    ecall
