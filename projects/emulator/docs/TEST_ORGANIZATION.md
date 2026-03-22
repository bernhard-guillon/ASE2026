# Test Directory Organization

## Structure Overview

```
emulator/
├── blackbox_tests/
│   ├── asm/                        # Assembly-based tests
│   │   ├── basic/                  # Basic instruction tests (9 tests)
│   │   │   ├── arithmetic/
│   │   │   ├── comparisons/
│   │   │   ├── fibonacci/
│   │   │   ├── hello/
│   │   │   ├── immediates/
│   │   │   ├── loops/
│   │   │   ├── memory/
│   │   │   ├── shifts/
│   │   │   └── stack/
│   │   ├── branches/               # Branch instruction tests (3 tests)
│   │   ├── edge_cases/             # Edge case tests (4 tests)
│   │   ├── jumps/                  # Jump instruction tests (2 tests)
│   │   ├── memory/                 # Memory operation tests (3 tests)
│   │   ├── syscalls/               # Syscall tests (3 tests)
│   │   └── upper_immediates/       # Upper immediate tests (2 tests)
│   │
│   └── c/                          # C-based tests (organized by feature)
│       ├── hello/                  # Hello world examples
│       │   ├── hello_c2.bin
│       │   ├── hello_c2.elf
│       │   ├── test.bin
│       │   ├── test.c
│       │   └── test.elf
│       ├── fibonacci/              # Fibonacci implementation
│       │   ├── fib.bin
│       │   ├── fib.c
│       │   └── fib.elf
│       ├── malloc/                 # Memory allocation tests
│       │   ├── malloc.c
│       │   ├── malloc_debug.*
│       │   ├── malloc_test.*
│       │   ├── malloc_test2.*
│       │   ├── malloc_large.*
│       │   └── malloc_multi.*
│       ├── file_io/                # File I/O tests
│       │   ├── file_read.*
│       │   ├── file_write.*
│       │   ├── test_open.*
│       │   ├── test_read.*
│       │   ├── test_lseek.*
│       │   ├── test_random_access.*
│       │   ├── test_data.txt
│       │   └── test_*.txt
│       └── recursion/              # Recursion tests
│           ├── test_recursion.bin
│           ├── test_recursion.c
│           ├── test_recursion.elf
│           ├── test_recursion_advanced.bin
│           ├── test_recursion_advanced.c
│           └── test_recursion_advanced.elf
│
├── run_blackbox_tests.py           # Test runner (updated for new structure)
├── crt0.s                          # C runtime startup code (shared)
├── syscalls.s                      # System call wrappers (shared)
├── linker.ld                       # Linker script (shared)
├── *.cpp, *.h                      # Core emulator source
└── build/                          # Build directory
```

## Test Categories

### Assembly Tests (blackbox_tests/asm/)
**Total: 26 tests** - Comprehensive RISC-V instruction testing

| Category | Tests | Purpose |
|----------|-------|---------|
| basic | 9 | Arithmetic, comparisons, loops, memory, stack operations |
| branches | 3 | Conditional branch instructions |
| edge_cases | 4 | Edge cases in instructions (LSB, large immediates, etc.) |
| jumps | 2 | JAL and JALR instructions |
| memory | 3 | Load/store operations with different widths |
| syscalls | 3 | System call integration (write, exit, exit codes) |
| upper_immediates | 2 | LUI and AUIPC instructions |

**Running Assembly Tests:**
```bash
python3 run_blackbox_tests.py                    # Run all tests
python3 run_blackbox_tests.py -p basic           # Run category
python3 run_blackbox_tests.py -p basic/hello     # Run specific test
```

### C Tests (blackbox_tests/c/)
**Total: 13+ programs** - Feature-focused testing with system calls

| Category | Programs | Features Tested |
|----------|----------|-----------------|
| hello | 3 | Basic I/O, program structure |
| fibonacci | 1 | Recursion, computation |
| malloc | 6 | Memory allocation, brk(), mmap2(), munmap() |
| file_io | 8 | File operations, read(), write(), lseek(), random access |
| recursion | 2 | Simple and advanced recursion, mutual recursion |

**Key Test Programs:**

#### hello/
- `hello_c2` - Simple printf-like output
- `test.c` - Basic arithmetic and I/O

#### fibonacci/
- `fib.c` - Recursive fibonacci computation

#### malloc/
- `malloc.c` - malloc/free implementation using mmap2
- `malloc_debug.c` - Malloc with debug output
- `malloc_test.c` - Basic allocation test
- `malloc_test2.c` - Multi-region allocation
- `malloc_large.c` - Large allocation (>1MB)
- `malloc_multi.c` - Concurrent allocations

#### file_io/
- `file_read.c` - Read existing files
- `file_write.c` - Create and write files
- `test_open.c` - File opening verification
- `test_read.c` - Read operations
- `test_lseek.c` - Seek and overwrite operations
- `test_random_access.c` - Complex random access patterns

#### recursion/
- `test_recursion.c` - Simple recursion (sum, countdown, fibonacci)
- `test_recursion_advanced.c` - Mutual recursion, deep calls, indirect recursion

**Note:** C tests are **not** automatically run by the test runner (they require compilation with gcc). They serve as manual verification tools.

## Compilation and Execution

### Compiling C Programs

To compile a C test program:
```bash
cd /path/to/emulator
riscv64-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib -static \
    -T linker.ld -o program.elf \
    crt0.s syscalls.s blackbox_tests/c/category/program.c

riscv64-elf-objcopy -O binary program.elf program.bin
```

### Running Tests

```bash
# Run all assembly tests
python3 run_blackbox_tests.py

# Run with verbose output on failures
python3 run_blackbox_tests.py -v

# Run specific category
python3 run_blackbox_tests.py -p malloc

# Run C test program directly
./build/emulator_runner blackbox_tests/c/fibonacci/fib.bin

# Run with verbose output
./build/emulator_runner -v blackbox_tests/c/malloc/malloc_test.bin
```

## Adding New Tests

### Adding Assembly Tests
1. Create directory: `blackbox_tests/asm/category/testname/`
2. Add files:
   - `test.s` - Assembly source
   - `config.txt` - Test configuration (exit code, timeout)
   - `expected.txt` - Expected output
3. Run: `python3 run_blackbox_tests.py -p category`

### Adding C Tests
1. Create directory: `blackbox_tests/c/category/` (if new)
2. Add files:
   - `program.c` - C source
   - Optionally: supporting files, data files
3. Compile: Follow compilation steps above
4. Test: Run binary with emulator_runner

## Test Execution Flow

### Assembly Tests (Automated)
```
run_blackbox_tests.py
├─ Discover: Find all test.s files in blackbox_tests/asm/
├─ Compile: Assemble, link, and convert to binary
├─ Run: Execute with emulator_runner
├─ Validate: Check output and exit code
└─ Report: Summary of passed/failed tests
```

### C Tests (Manual)
```
Compilation:
program.c → compile (riscv64-elf-gcc) → program.elf → binary (objcopy) → program.bin

Execution:
program.bin → emulator_runner → stdout/exit code
```

## Benefits of This Organization

✅ **Clear Separation** - Assembly tests separate from C tests
✅ **Scalable** - Easy to add new test categories
✅ **Organized** - C tests grouped by functionality
✅ **Maintainable** - Each test in its own directory
✅ **Professional** - Follows industry testing practices
✅ **Clean Main Directory** - Source code and tests separated

## Migration from Old Structure

**What Moved:**
- All `.c`, `.bin`, `.elf` files moved to `blackbox_tests/c/`
- Assembly tests moved to `blackbox_tests/asm/`
- Test runner updated to find tests in new location

**What Stayed:**
- `crt0.s`, `syscalls.s`, `linker.ld` - Shared compilation helpers
- `run_blackbox_tests.py` - Test runner (updated)
- Core emulator source code

**Verification:**
All 26 assembly tests still pass after reorganization ✅
