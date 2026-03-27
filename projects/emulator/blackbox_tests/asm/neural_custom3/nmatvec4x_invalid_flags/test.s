# CUSTOM3 NMATVEC4X invalid flags must return status=ERR_INVALID_PTR (1)

.section .text
.globl _start

_start:
    li t0, 0x300          # desc
    li t1, 0x340          # input
    li t2, 0x380          # weights
    li t3, 0x3C0          # bias
    li t4, 0x400          # output

    # descriptor
    sw t1, 0(t0)
    sw t2, 4(t0)
    sw t3, 8(t0)
    sw t4, 12(t0)
    li t5, 1
    sw t5, 16(t0)         # input_len
    sw t5, 20(t0)         # output_len
    sw t5, 24(t0)         # flags = 1 (invalid)
    sw x0, 28(t0)

    li t5, 0x3f800000
    sw t5, 0(t1)
    sw t5, 0(t2)
    sw x0, 0(t3)
    sw x0, 0(t4)

    # opid=4, rd=a0(10), rs1=t0(5), rs2=0, rs3=0, opcode=0x7B
    .word 0x2000557B

    # status must be 1 for invalid flags
    li t1, 1
    bne a0, t1, fail

    li a0, 0
    li a7, 93
    ecall

fail:
    li a0, 61
    li a7, 93
    ecall
