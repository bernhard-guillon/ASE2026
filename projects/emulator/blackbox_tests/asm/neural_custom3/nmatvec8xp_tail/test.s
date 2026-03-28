# CUSTOM3 NMATVEC8XP tail-width check (output_len not divisible by 8)

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
    sw t5, 16(t0)         # input_len = 1
    li t5, 3
    sw t5, 20(t0)         # output_len = 3 (tail for lane8)
    sw x0, 24(t0)
    sw x0, 28(t0)

    # input[0] = 1.0
    li t5, 0x3f800000
    sw t5, 0(t1)

    # weights row (1x3): [1,2,3]
    li t5, 0x3f800000
    sw t5, 0(t2)
    li t5, 0x40000000
    sw t5, 4(t2)
    li t5, 0x40400000
    sw t5, 8(t2)

    # bias = 0
    sw x0, 0(t3)
    sw x0, 4(t3)
    sw x0, 8(t3)

    # opid=6, rd=a0(10), rs1=t0(5), rs2=0, rs3=0, opcode=0x7B
    .word 0x3000557B

    # Ensure status == 0
    bne a0, x0, fail_status

    # Verify output vector: [1.0, 2.0, 3.0]
    lw t6, 0(t4)
    li t5, 0x3f800000
    bne t6, t5, fail_data
    lw t6, 4(t4)
    li t5, 0x40000000
    bne t6, t5, fail_data
    lw t6, 8(t4)
    li t5, 0x40400000
    bne t6, t5, fail_data

    li a0, 0
    li a7, 93
    ecall

fail_status:
    li a0, 71
    li a7, 93
    ecall

fail_data:
    li a0, 72
    li a7, 93
    ecall
