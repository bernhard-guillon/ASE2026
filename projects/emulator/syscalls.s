# RISC-V syscall wrappers
# These provide the syscall interface to C programs

.section .text
.globl write
.globl exit

# write(int fd, const void *buf, unsigned long count) -> long
# fd: a0
# buf: a1  
# count: a2
# Returns: a0 (bytes written)
write:
    li a7, 64              # syscall number for write
    ecall
    ret

# exit(int status) -> void
# status: a0
exit:
    li a7, 93              # syscall number for exit
    ecall
    ret
