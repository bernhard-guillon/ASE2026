# Unit Test Coverage Analysis & Plan

## Executive Summary

Current unit test coverage: **~55% of implemented features**

- **RV32I Instructions**: ~90% coverage (38/40+ tests, missing edge cases)
- **Syscalls**: **20% coverage** (2/10 tests)
  - **File I/O syscalls**: **0% coverage** (5 syscalls, 0 tests)
  - **Memory management**: **0% coverage** (3 syscalls, 0 tests)

### Critical Gaps
1. **Zero file I/O syscall tests** despite implementing openat(56), read(63), close(57), lseek(19), and write(64) to files
2. **Zero memory syscall tests** despite implementing brk(214), mmap2(192), munmap(215)
3. **Missing edge case tests** for instructions (misaligned access, boundary shifts, max immediates)

---

## Detailed Analysis

### Current Test Files
- `test_cpu.cpp` - 19 tests (CPU state, PC, registers)
- `test_memory.cpp` - 5 tests (Memory read/write operations)
- `test_instruction.cpp` - 10 tests (Instruction decoding)
- `test_execution.cpp` - 80+ tests (Instruction execution)
- `test_emulator.cpp` - 12 tests (End-to-end emulation)
- **Total**: ~135 unit tests

---

## Missing Unit Tests by Category

### 1. File I/O Syscalls (Priority: **CRITICAL**)

Implemented but **completely untested**: openat(56), read(63), close(57), lseek(19), write(64)

#### openat(56) - File Opening
```
Priority: HIGH
Tests needed: 5
├─ io-openat-basic: Open existing file in read mode
├─ io-openat-wronly: Open file with O_WRONLY flag  
├─ io-openat-creat: Create new file with O_CREAT
├─ io-openat-append: Open with O_APPEND flag
└─ io-openat-error: Error handling (invalid paths)
```

#### read(63) - File Reading
```
Priority: HIGH
Tests needed: 5 (depends on openat)
├─ io-read-basic: Read from opened file
├─ io-read-large: Read with count > file size
├─ io-read-eof: Read at EOF (returns 0)
├─ io-read-multiple: Sequential reads advance position
└─ io-read-error: Error handling (invalid fd)
```

#### close(57) - File Closing
```
Priority: HIGH
Tests needed: 4
├─ io-close-valid: Close valid file descriptor
├─ io-close-invalid: Close error handling
├─ io-close-stdio: Closing stdin/stdout/stderr behavior
└─ io-close-reuse: FD can be reused after close
```

#### lseek(19) - File Positioning
```
Priority: HIGH
Tests needed: 5 (depends on read)
├─ io-lseek-set: SEEK_SET (absolute positioning)
├─ io-lseek-cur: SEEK_CUR (relative to current position)
├─ io-lseek-end: SEEK_END (relative to file end)
├─ io-lseek-negative: Error handling (negative offset)
└─ io-lseek-beyond: Seeking beyond file bounds
```

#### write(64) to Files
```
Priority: HIGH
Tests needed: 4 (depends on openat with O_WRONLY)
├─ io-write-files: Write to fd >= 3 (regular file)
├─ io-write-multiple: Multiple writes accumulate correctly
├─ io-write-append: O_APPEND mode writes at end
└─ io-write-error: Error handling (write to closed fd)
```

**Subtotal: 23 file I/O tests needed**

---

### 2. Memory Management Syscalls (Priority: **CRITICAL**)

Implemented but **completely untested**: brk(214), mmap2(192), munmap(215)

#### brk(214) - Heap Management
```
Priority: HIGH
Tests needed: 4
├─ mem-brk-set: Set heap break address
├─ mem-brk-query: Query current break (arg=0)
├─ mem-brk-invalid: Invalid break address error handling
└─ mem-brk-multiple: Sequential brk calls
```

#### mmap2(192) - Memory Mapping
```
Priority: HIGH
Tests needed: 5
├─ mem-mmap-anon: MAP_ANONYMOUS allocation
├─ mem-mmap-fixed: MAP_FIXED flag allocation
├─ mem-mmap-align: Page alignment verification
├─ mem-mmap-oomem: Out of memory error handling
└─ mem-mmap-both-flags: Combined flags (ANON + FIXED)
```

#### munmap(215) - Memory Unmapping
```
Priority: HIGH
Tests needed: 4 (depends on mmap tests)
├─ mem-munmap-valid: Unmap valid region
├─ mem-munmap-invalid: Unmap invalid region error handling
├─ mem-munmap-partial: Partial unmap of region
└─ mem-munmap-multiple: Sequential unmaps
```

**Subtotal: 13 memory syscall tests needed**

---

### 3. Instruction Edge Cases (Priority: **MEDIUM**)

Current coverage: ~90%, but missing edge cases

#### Load/Store Edge Cases
```
Priority: HIGH
Tests needed: 2
├─ instr-load-unaligned: Misaligned load handling
└─ instr-store-unaligned: Misaligned store handling
```

#### Shift Operation Boundaries
```
Priority: MEDIUM
Tests needed: 1
└─ instr-shift-boundary: Shift by 31, 32, >31 bits
```

#### Immediate Field Boundaries
```
Priority: MEDIUM
Tests needed: 1
└─ instr-immediate-max: Max positive (2047), max negative (-2048)
```

#### Other Edge Cases
```
Priority: MEDIUM
Tests needed: 2
├─ instr-load-uninit: Load from uninitialized memory
└─ instr-branch-max-offset: Maximum branch offset (±4096)
```

**Subtotal: 6 instruction edge case tests needed**

---

## Implementation Plan

### Phase 1: File I/O Syscall Tests (HIGH PRIORITY)
**Estimated effort**: 2-3 hours
**File**: `test_file_io_syscalls.cpp` (new)

Structure:
- Setup: Create temporary test files in `/tmp`
- For each syscall group:
  - Basic functionality tests
  - Error handling tests
  - Integration tests (combining multiple syscalls)

Tests by dependencies:
1. First: openat tests (no dependencies)
2. Then: read/close/lseek (depend on openat)
3. Finally: write tests (depend on openat)

### Phase 2: Memory Management Syscall Tests (HIGH PRIORITY)
**Estimated effort**: 1.5-2 hours
**File**: `test_memory_syscalls.cpp` (new)

Structure:
- Setup: Initialize emulator with sufficient memory
- For each syscall group:
  - Basic allocation/deallocation
  - Edge cases and error conditions
  - Integration tests (alloc → use → free)

Tests by dependencies:
1. First: brk tests (no dependencies)
2. Then: mmap tests (can be independent)
3. Finally: munmap tests (depends on mmap)

### Phase 3: Instruction Edge Case Tests (MEDIUM PRIORITY)
**Estimated effort**: 1-1.5 hours
**File**: `test_instruction_edges.cpp` (new)

Structure:
- Extend `test_execution.cpp` or create separate file
- For each edge case:
  - Boundary value testing
  - Error condition verification
  - Behavior documentation

---

## Test Implementation Guide

### File I/O Tests Template
```cpp
#include <gtest/gtest.h>
#include <fstream>
#include <cstdlib>
#include "Emulator.h"

class FileIOTest : public ::testing::Test {
protected:
    Emulator emulator{4096};
    std::string test_file = "/tmp/test_file.txt";
    
    void SetUp() override {
        emulator.reset();
        // Create test file with known content
    }
    
    void TearDown() override {
        // Clean up test files
    }
};

TEST_F(FileIOTest, OpenExistingFile) {
    // Write path string to emulator memory
    // Call openat syscall
    // Verify fd returned is >= 3
    // Verify fd is valid
}
```

### Memory Syscall Tests Template
```cpp
#include <gtest/gtest.h>
#include "Emulator.h"

class MemorySyscallTest : public ::testing::Test {
protected:
    Emulator emulator{16384};  // 16KB memory
    
    void SetUp() override {
        emulator.reset();
    }
};

TEST_F(MemorySyscallTest, BrkSetAndQuery) {
    // Use syscall to set brk
    // Query with brk(0)
    // Verify returned address matches
}
```

---

## Test Count Summary

| Category | Needed | Effort |
|----------|--------|--------|
| File I/O Syscalls | 23 | ~2-3 hrs |
| Memory Syscalls | 13 | ~1.5-2 hrs |
| Instruction Edges | 6 | ~1-1.5 hrs |
| **TOTAL** | **42** | **~5-6.5 hrs** |

---

## Expected Impact

After implementation:
- **File I/O coverage**: 0% → 100%
- **Memory Syscall coverage**: 0% → 100%
- **Instruction coverage**: 90% → 95%+
- **Overall syscall coverage**: 20% → 70%+
- **Total unit tests**: 135 → 177 tests

---

## Validation Strategy

1. **New tests must pass** with current implementation
2. **Blackbox tests must continue to pass** (no regressions)
3. **All 177 unit tests + 26 asm + 16 C program tests must pass**
4. **Code coverage analysis** (optional: measure statement coverage)

---

## Notes

- Tests should be **independent** and use temporary files/memory
- Tests should **clean up** after themselves (temporary files)
- Tests should **cover both success and error paths**
- Tests should **document expected behavior** via comments
- Consider creating helper functions for:
  - Writing strings to emulator memory
  - Calling syscalls from assembly patterns
  - Verifying file contents after I/O operations
