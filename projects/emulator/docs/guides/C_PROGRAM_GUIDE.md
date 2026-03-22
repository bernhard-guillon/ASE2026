# C Program Development Guide for RV32I Emulator

## Current Capabilities

Your emulator can now run C programs compiled for bare-metal RISC-V. This guide explains what works, what doesn't, and how to write compatible code.

### ✅ Supported Features

1. **Basic C Data Types and Operations**
   - Integers (int, char, unsigned types)
   - Pointers (basic usage)
   - Arrays (stack-allocated)
   - Structs (should work, untested)

2. **Control Flow**
   - if/else conditions
   - for/while loops
   - Function calls (with proper stack frames)
   - Return values

3. **I/O Operations**
   - write(1, buf, len) → stdout
   - write(2, buf, len) → stderr

4. **Program Control**
   - exit(code) → terminate with exit code
   - brk(addr) → query/set heap break (basic)

5. **Memory Management**
   - Stack allocation (automatic)
   - Static allocation (via static arrays)
   - Basic heap simulation

### ❌ Unsupported Features (Currently)

1. **Dynamic Allocation**
   - malloc() - would need mmap2 syscall
   - free() - would need munmap syscall
   - calloc(), realloc() - depend on malloc

2. **File Operations**
   - open() - would need openat syscall
   - read() - would need read syscall
   - fopen(), fread(), etc. - depend on open/read
   - File streams (FILE structure)

3. **Advanced C Library Functions**
   - printf/scanf - requires file I/O and formatting
   - string functions (strcpy, strlen, etc.) - mostly available as builtins
   - math functions (sin, cos, sqrt) - would need FPU or soft-float
   - memory functions (memcpy, memset) - may work via compiler builtins

4. **System Features**
   - Signals (signal(), sigaction)
   - Process management (fork(), exec())
   - Threads (pthread)
   - Environment variables (getenv)

## Compilation Instructions

### Basic Setup
```bash
# Set working directory
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator

# Create your_program.c with C code below
# Then compile with:
riscv64-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib \
    -o your_program.elf crt0.s your_program.c syscalls.s -T linker.ld

# Convert to binary
riscv64-elf-objcopy -O binary your_program.elf your_program.bin

# Run
./build/emulator_runner your_program.bin
```

### Key Compilation Flags
- `-march=rv32i` - Target 32-bit RISC-V with base instruction set
- `-mabi=ilp32` - Use 32-bit ABI (ints, longs, pointers are 32-bit)
- `-nostdlib` - Don't link standard library (we provide minimal runtime)
- `-T linker.ld` - Use custom linker script for bare-metal layout

## Example Programs

### Example 1: Hello World
```c
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    const char *msg = "Hello!\n";
    write(1, msg, 7);
    return 0;
}
```

### Example 2: Arithmetic and Printing Single Digits
```c
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    int a = 10, b = 20;
    int sum = a + b;
    
    // Convert to ASCII (only works for single digits)
    char digit = '0' + (sum / 10);
    write(1, &digit, 1);
    
    digit = '0' + (sum % 10);
    write(1, &digit, 1);
    
    write(1, "\n", 1);
    return 0;
}
```

### Example 3: Arrays and Loops
```c
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    int i;
    
    for (i = 0; i < 5; i++) {
        char digit = '0' + arr[i];
        write(1, &digit, 1);
        write(1, " ", 1);
    }
    
    write(1, "\n", 1);
    return 0;
}
```

### Example 4: Functions
```c
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(5, 7);
    // ... print result as shown in Example 2
    return 0;
}
```

## Important Notes

### Memory Layout
- Code starts at address 0x00000000
- Stack grows downward from 0x10000 (65536)
- Heap starts around 0x1000 (4096)
- Total memory: 65536 bytes (64 KB)

### Stack Pointer Initialization
The emulator_runner automatically initializes sp (x2) to 65536. This is critical for C code that uses the stack for local variables and function calls.

### Writing Numbers to Output

Since we only have write() syscall (no printf), here are workarounds:

**For single digits (0-9):**
```c
char digit = '0' + value;
write(1, &digit, 1);
```

**For multi-digit numbers, convert manually:**
```c
void print_int(int n) {
    if (n < 0) {
        write(1, "-", 1);
        n = -n;
    }
    
    if (n >= 10) {
        print_int(n / 10);
    }
    
    char digit = '0' + (n % 10);
    write(1, &digit, 1);
}
```

### Avoiding Unsupported Operations

**❌ DON'T USE:**
- malloc/free
- printf/fprintf/sprintf
- fopen/fread/fwrite
- memcpy/memset (unless compiler provides builtin)
- Division operators (triggers __divsi3 from libgcc)

**✅ DO USE:**
- Basic arithmetic (addition, subtraction, multiplication, bitwise)
- Arrays and structs
- Pointers (careful with bounds checking)
- Function calls
- Conditionals and loops
- Explicit write() syscalls

## Syscall Declarations

Your program needs to declare syscalls as external functions:

```c
// Essential syscalls
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

// Optional (not yet implemented)
// int brk(void *addr);
// int open(const char *path, int flags, int mode);
// int read(int fd, void *buf, unsigned long count);
// int close(int fd);
```

The actual syscall implementations are in syscalls.s (assembly wrappers) that:
1. Load syscall number into a7 (x17)
2. Load arguments into a0-a5 (x10-x15)
3. Execute ECALL instruction
4. Return result in a0

## Testing Your Programs

1. **Verify compilation:**
   ```bash
   riscv64-elf-objdump -d your_program.elf | head -50
   ```
   Look for RV32I instructions (no RV64 sd/ld instructions)

2. **Check binary size:**
   ```bash
   ls -lh your_program.bin
   ```
   Should be < 65536 bytes

3. **Run with verbose output:**
   ```bash
   ./build/emulator_runner your_program.bin -v
   ```

4. **Check exit code:**
   ```bash
   ./build/emulator_runner your_program.bin
   echo "Exit code: $?"
   ```

## Future Capabilities

As we implement more syscalls, these features will become available:

1. **After mmap2/munmap:** Dynamic allocation with malloc/free
2. **After open/read/close:** File I/O, loading data files
3. **After signal handling:** Interrupt support, profiling
4. **After libc integration:** printf, standard library functions

## Debugging Tips

1. **Instruction count limit exceeded?**
   - Your program has an infinite loop
   - Check loop conditions and termination

2. **Memory access out of bounds?**
   - Your code is accessing memory beyond 65KB
   - Reduce array sizes or increase emulator memory

3. **Unsupported syscall?**
   - You called a syscall we don't implement yet
   - Check LINUX_SYSCALLS.md for what's available

4. **Wrong output?**
   - Syscall numbers differ on RV32 (not matching x86 or ARM)
   - Use the correct RISC-V syscall numbers

## Resources

- Example programs: see hello_c2.bin, test.bin, fib.bin
- Syscall list: LINUX_SYSCALLS.md
- Compilation reference: run `riscv64-elf-gcc --help`
- RISC-V ABI: https://github.com/riscv/riscv-elf-psabi-doc

