# CUSTOM3 NMATVEC4X overflowed descriptor sizes must return status=ERR_INVALID_PTR (1)

.section .text
.globl _start

_start:
    li t0, 0x300          # desc
    li t1, 0x340          # input
    li t2, 0x380          # weights
    li t3, 0x3C0          # bias
    li t4, 0x400          # output

    # descriptor with overflow-inducing length
    sw t1, 0(t0)
    sw t2, 4(t0)
    sw t3, 8(t0)
    sw t4, 12(t0)
    li t5, 0x40000000
    sw t5, 16(t0)         # input_len = huge -> input_len * 4 overflows 32-bit
    li t5, 8
    sw t5, 20(t0)         # output_len
    sw x0, 24(t0)         # flags = 0
    sw x0, 28(t0)         # reserved = 0

    # opid=4, rd=a0(10), rs1=t0(5), rs2=0, rs3=0, opcode=0x7B
    .word 0x2000557B

    # status must be 1 for invalid ptr/size overflow
    li t1, 1
    bne a0, t1, fail

    li a0, 0
    li a7, 93
    ecall

fail:
    li a0, 101
    li a7, 93
    ecall
