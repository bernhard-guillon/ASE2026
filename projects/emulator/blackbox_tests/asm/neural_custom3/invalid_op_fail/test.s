# CUSTOM3 invalid op must fail loud (non-zero exit)

.section .text
.globl _start

_start:
    # opid=31 invalid, rd=a0(10), opcode=0x7B
    .word 0xF000057B

    # If execution reaches here, failure path did not trigger
    li a0, 0
    li a7, 93
    ecall
