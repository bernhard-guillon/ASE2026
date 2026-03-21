# RISC-V Linux Syscall Integration

## Implemented Syscalls

### 64 - write(fd, buf, count)
```c
ssize_t write(int fd, const void *buf, size_t count);
```
- **Status**: ✅ Fully implemented
- **Behavior**: Outputs to stdout (fd=1) or stderr (fd=2)
- **Returns**: Number of bytes written
- **Used by**: All test programs, standard output

### 93 - exit(status) 
```c
void exit(int status);
```
- **Status**: ✅ Fully implemented  
- **Behavior**: Halts emulator, captures exit code
- **Returns**: Never (terminates execution)
- **Used by**: Program termination, exit codes

### 214 - brk(addr)
```c
void *brk(void *addr);
```
- **Status**: ✅ Fully implemented
- **Behavior**: Set/query heap break address
- **Returns**: New break on success, old break on failure
- **Used by**: malloc/free implementations, heap management

### 192 - mmap2(addr, len, prot, flags, fd, offset)
```c
void *mmap2(void *addr, size_t len, int prot, int flags, int fd, long pgoffset);
```
- **Status**: ✅ Fully implemented (Phase 2)
- **Behavior**: Maps memory pages (MAP_ANONYMOUS for zero-initialized allocations)
- **Features**: Supports MAP_ANONYMOUS and MAP_FIXED flags
- **Returns**: Mapped address or -1 on error
- **Used by**: Dynamic memory allocation, malloc implementation

### 215 - munmap(addr, len)
```c
int munmap(void *addr, size_t len);
```
- **Status**: ✅ Fully implemented (Phase 2)
- **Behavior**: Unmaps previously mapped memory regions
- **Returns**: 0 on success, -1 on error
- **Used by**: Memory deallocation, free implementation

### 56 - openat(dirfd, pathname, flags, mode)
```c
int openat(int dirfd, const char *pathname, int flags, mode_t mode);
```
- **Status**: ✅ Fully implemented (Phase 3)
- **Behavior**: Opens or creates a file
- **Features**: Supports O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_APPEND
- **Returns**: File descriptor (≥3) or -1 on error
- **Used by**: File I/O operations, reading/writing files

### 63 - read(fd, buf, count)
```c
ssize_t read(int fd, void *buf, size_t count);
```
- **Status**: ✅ Fully implemented (Phase 3)
- **Behavior**: Reads bytes from open file descriptor
- **Features**: Writes data into emulator memory, handles EOF
- **Returns**: Bytes read or -1 on error
- **Used by**: Reading file contents

### 57 - close(fd)
```c
int close(int fd);
```
- **Status**: ✅ Fully implemented (Phase 3)
- **Behavior**: Closes file descriptor and frees resources
- **Returns**: 0 on success, -1 on error
- **Used by**: Closing files and releasing descriptors

## Required for musl libc Support

### Core Syscalls Needed for Initialization
| # | Syscall | Purpose | Priority |
|---|---------|---------|----------|
| 39 | getpid | Get process ID | High |
| 100 | clock_gettime | Time queries | Medium |
| 169 | gettimeofday | Get time | Medium |
| 174 | rt_sigaction | Signal handling | High |
| 180 | pread64 | Positioned read | Medium |

### File I/O (✅ PHASE 3 COMPLETE)
| # | Syscall | Purpose | Status |
|---|---------|---------|--------|
| 56 | openat | Open file | ✅ Implemented |
| 57 | close | Close file descriptor | ✅ Implemented |
| 63 | read | Read from file | ✅ Implemented |
| 64 | write | Write to file | ✅ Implemented |
| 82 | lseek | Seek in file | Planned |

### String/Math (Runtime Support)
These are NOT syscalls but helper functions needed:
- `__divsi3` - Signed 32-bit division (needed by GCC)
- `__modsi3` - Signed 32-bit modulo
- `__udivsi3` - Unsigned 32-bit division  
- `__umodsi3` - Unsigned 32-bit modulo
- `memcpy` - Memory copy
- `memset` - Memory set
- `strlen` - String length

**Current Status**: Not implemented, need libgcc or custom implementations

## Current Limitations

### What Works
✅ Write to stdout/stderr
✅ Exit with code
✅ Stack initialization
✅ Local variables and arrays
✅ Function calls (with explicit syscall wrappers)
✅ Basic arithmetic and loops
✅ Heap break tracking (brk syscall)
✅ Dynamic malloc/free (mmap2 + munmap syscalls)
✅ Multiple concurrent allocations
✅ File I/O (open, read, close syscalls)
✅ Reading existing files
✅ Creating new files

### What Doesn't Work  
❌ Signal handling (would need rt_sigaction)
❌ Process creation (would need fork/clone)
❌ Shared libraries (would need mmap + ELF loader)
❌ Floating point (would need M extension + FP support)
❌ Division operations (would need __divsi3 from libgcc)
❌ Seeking in files (would need lseek syscall)

## Integration Roadmap

### Phase 1: Foundation (✅ DONE)
- ✅ Basic write(1, ...) and exit()
- ✅ Stack pointer initialization  
- ✅ brk() syscall
- ✅ C program compilation with RV32I

### Phase 2: Memory Management (✅ DONE)
- ✅ mmap2(192) syscall for anonymous memory mapping
- ✅ munmap(215) syscall for memory deallocation
- ✅ malloc/free C implementation using mmap2
- ✅ Multiple allocation support
- ✅ Dynamic arrays and data structures
- ✅ Increased memory to 1GB for large allocations

### Phase 3: File I/O (✅ DONE)
- ✅ openat(56) syscall for opening/creating files
- ✅ read(63) syscall for reading from files
- ✅ close(57) syscall for closing file descriptors
- ✅ Test with file creation and reading
- ✅ Support for O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_APPEND

### Phase 4: Advanced I/O (NEXT)
1. Implement lseek(19) syscall for seeking in files
2. Add write(64) support for file descriptors (currently only stdout/stderr)
3. Test random access and file seeking

### Phase 4: libc Integration (AFTER PHASE 3)
1. Add division helpers (__divsi3, etc.) via libgcc
2. Link against musl libc
3. Test with real C programs using stdio

### Phase 5: Advanced Features (FUTURE)
1. Signal handling (rt_sigaction)
2. Process management (getpid, fork)
3. ELF file format support
4. Shared library loading

## Testing Examples

The C programs in this directory demonstrate syscall usage:

1. **hello_c2.bin** - Uses: write(1), exit(0)
2. **test.bin** - Uses: write(1), exit(0), arithmetic
3. **fib.bin** - Uses: write(1), exit(0), arrays, loops
4. **malloc_test.bin** - Uses: brk (implicit via static allocation)

To add new tests, compile C programs with:
```bash
riscv64-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib \
    -o program.elf crt0.s program.c syscalls.s -T linker.ld
riscv64-elf-objcopy -O binary program.elf program.bin
./build/emulator_runner program.bin
```

## Syscall Reference

Full Linux RISC-V ABI syscall numbers:
https://github.com/torvalds/linux/blob/master/arch/riscv/include/asm/unistd.h

