# CUSTOM3 NVRELUX smoke test

.section .text
.globl _start

_start:
    # opid=1, rd=a0(10), rs1=a1(11), rs2=a2(12), rs3=a3(13), opcode=0x7B
    .word 0x0B58B57B

    li a7, 93
    ecall
