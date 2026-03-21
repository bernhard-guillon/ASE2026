# Phase 4: Advanced File I/O - Summary

## Objective
Implement file seeking and extend file I/O syscalls to support random access operations and writing to file descriptors.

## Implementation Details

### 1. lseek(19) Syscall - File Positioning
- **What**: Implements file seeking with SEEK_SET, SEEK_CUR, SEEK_END
- **How**: 
  - Validates file descriptor existence
  - Calculates new position based on whence parameter
  - Updates both get and put pointers on underlying fstream
  - Tracks file positions in file_positions_ map
- **Key Code**: Emulator.cpp case 19: lines 369-445
- **Error Handling**: Returns -1 for invalid fd or negative seek position

### 2. Extended write(64) - File Descriptor Support
- **What**: Extended write syscall to support writing to open files (fd ≥ 3)
- **How**:
  - Checks if fd is open file descriptor
  - Writes bytes directly to fstream
  - Flushes buffer after write
  - Tracks file position changes
- **Key Code**: Emulator.cpp case 64: lines 81-101
- **Previous**: Only supported fd=1 (stdout) and fd=2 (stderr)
- **New**: Now supports any valid open file descriptor

### 3. File Position Tracking
- **New Member**: file_positions_ map in Emulator.h
- **Tracking Points**:
  - Initialize to 0 on file open (openat)
  - Update on read() and write() operations
  - Update on lseek() calls
  - Clean up on close()
  - Clear on reset()

### 4. System Call Changes
**File Descriptor Lifecycle**:
1. openat(56): Creates fd, initializes position to 0
2. read(63): Reads and increments position
3. write(64): **NEW** - Writes to files and increments position
4. lseek(19): **NEW** - Updates position without I/O
5. close(57): Closes fd and cleans up position tracking

## Test Programs Created

### test_lseek.c
- Creates file with specific content
- Writes to file using write(fd)
- Seeks back to middle position
- Overwrites content
- Reopens and reads result
- **Expected**: File contents match seeks and overwrites

### test_random_access.c
- Writes initial content "0123456789"
- Seeks to position 2, writes "XX"
- Seeks to position 7, writes "YY"
- Seeks to end, appends "!"
- Reads entire file
- **Expected**: Result is "01XX456YY9!"

## Test Results
```
✓ All 26 blackbox tests passed (no regressions)
✓ test_lseek.c: PASS - File contents: Hello RISC-V
✓ test_random_access.c: PASS - Result: 01XX456YY9! (expected: 01XX456YY9!)
```

## Code Changes

### Emulator.h
- Added file_positions_ map to track per-fd offset
- Maps int (fd) -> uint32_t (current offset)

### Emulator.cpp
- case 64 (write): Extended to handle fd ≥ 3 with position tracking
- case 63 (read): Added position tracking after read
- case 56 (openat): Initialize file_positions_[fd] = 0
- case 57 (close): Clean up file_positions_[fd]
- case 19 (lseek): **NEW** Complete implementation
- reset(): Clear file_positions_ map

### syscalls.s
- Added .globl lseek
- Added lseek: label with ecall for syscall 19

## Architectural Decisions

### Why Track File Positions?
- Standard POSIX behavior: each fd maintains independent position
- Required for stateful file operations
- Enables multiple reads/writes without explicit lseeks

### Why SEEK_END Requires File Size Query?
- Need to calculate actual file end for SEEK_END
- Use seekg(0, ios::end) and tellg() to find end
- Positions are 32-bit to match RISC-V ABI

### Write Support for All FDs
- No distinction needed between stdout/file fds
- Unified code path ensures consistency
- Enables logging to files in addition to stdout

## Known Limitations

1. **No file seek persistence between programs**: Each run starts fresh
2. **No fstat support**: Can't query file size without seeking to end
3. **No file offset validation**: Seeking past EOF is allowed (standard behavior)
4. **Platform-specific**: File operations depend on host filesystem

## Integration with Existing Phases

- **Phase 1**: Basic syscalls remain unchanged
- **Phase 2**: Memory management unaffected
- **Phase 3**: Enhanced write() syscall, open/read/close unchanged
- **Phase 4**: Adds lseek and file position state management

## Future Work

### Phase 5: libc Integration
- Will need more complex syscalls for libc
- File position tracking will be essential for stdio buffering

### Phase 6: Advanced Features
- fstat/stat for metadata
- lstat for symlink handling
- fcntl for file control operations

## Summary
Phase 4 completes the core file I/O functionality with random access support. The emulator can now:
- ✅ Create and write files
- ✅ Read file contents
- ✅ Seek to arbitrary positions
- ✅ Overwrite portions of files
- ✅ Track file positions per descriptor

This forms a complete foundation for advanced C programs that manipulate files with random access patterns, essential for database-like operations and any program that needs to read/modify specific file regions.
