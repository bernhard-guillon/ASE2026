# RISC-V syscall wrappers
# These provide the syscall interface to C programs

.section .text
.globl write
.globl exit
.globl mmap
.globl munmap
.globl brk

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

# mmap2(void *addr, size_t len, int prot, int flags, int fd, off_t pgoffset) -> void*
# addr: a0
# len: a1
# prot: a2
# flags: a3
# fd: a4
# pgoffset: a5
# Returns: a0 (mapped address or -1 on error)
mmap:
    li a7, 192             # syscall number for mmap2 (RV32)
    ecall
    ret

# munmap(void *addr, size_t len) -> int
# addr: a0
# len: a1
# Returns: a0 (0 on success, -1 on error)
munmap:
    li a7, 215             # syscall number for munmap
    ecall
    ret

# brk(void *addr) -> void*
# addr: a0
# Returns: a0 (new break or old break on error)
brk:
    li a7, 214             # syscall number for brk
    ecall
    ret

