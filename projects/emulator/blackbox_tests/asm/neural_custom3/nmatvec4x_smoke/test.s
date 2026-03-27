# CUSTOM3 NMATVEC4X smoke test

.section .text
.globl _start

_start:
    li t0, 0x100
    # opid=4, rd=a0(10), rs1=t0(5), rs2=0, rs3=0, opcode=0x7B
    .word 0x2000557B

    li a7, 93
    ecall
