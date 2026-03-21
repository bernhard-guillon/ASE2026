# RISC-V syscall wrappers
# These provide the syscall interface to C programs

.section .text
.globl write
.globl exit
.globl mmap
.globl munmap
.globl brk
.globl open
.globl read
.globl close

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

# openat(int dirfd, const char *pathname, int flags, mode_t mode) -> int
# dirfd: a0
# pathname: a1
# flags: a2
# mode: a3
# Returns: a0 (file descriptor or -1 on error)
open:
    li a7, 56              # syscall number for openat
    ecall
    ret

# read(int fd, void *buf, size_t count) -> ssize_t
# fd: a0
# buf: a1
# count: a2
# Returns: a0 (bytes read or -1 on error)
read:
    li a7, 63              # syscall number for read
    ecall
    ret

# close(int fd) -> int
# fd: a0
# Returns: a0 (0 on success, -1 on error)
close:
    li a7, 57              # syscall number for close
    ecall
    ret

