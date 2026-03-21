# Model Bootloader Implementation Plan

## Problem Statement

Currently, neural network models are loaded from external binary files at runtime. We want to create a **bootloader system** similar to game cartridges or BIOS firmware:
- The bootloader is a RISC-V program that executes first
- It contains embedded model data 
- It initializes memory with the models at correct addresses
- Then jumps to application code or waits for further execution

**Goal**: Eliminate external file loading, embed models in executable.

## Architecture Overview

```
PyTorch Model (JSON)
    ↓
Model Compiler (Python)
    ↓
RISC-V Assembly + Embedded Data
    ↓
RISC-V Assembler + Linker
    ↓
Bootloader Binary (.bin)
    ↓
Emulator Loader (loads as first program)
    ↓
Bootloader executes → initializes memory → application continues
```

## 7 Implementation Phases

### Phase 1: Model Compiler - JSON to RISC-V Assembly

**Objective**: Create Python compiler that converts intermediate JSON format to RISC-V assembly with embedded binary data.

**Deliverables**:
- `model_compiler.py`: Main compiler class
  - Input: JSON intermediate format (from model_formats.py)
  - Output: RISC-V assembly (.s file)
  - Embeds binary model data as hex strings in `.data` section

**Algorithm**:
1. Load JSON intermediate format (model_formats.IntermediateFormat)
2. Create RISC-V assembly skeleton:
   ```asm
   .section .data
   .align 4
   model_data_generator:
       .incbin "path/to/generator.bin"
   
   model_data_recognizer:
       .incbin "path/to/recognizer.bin"
   
   .section .text
   .globl _start
   _start:
       # Code to initialize memory
       # (filled in Phase 2)
   ```

**Unit Tests**:
- Test JSON parsing
- Test `.incbin` directive generation
- Test section headers and alignment
- Verify output is valid RV32I assembly

**Black Box Tests**:
- Assemble generated .s file with riscv64-elf-as
- Verify object file contains correct sections
- Check data section size matches model size

**Exit Criteria**:
- ✓ Compiler generates valid RISC-V assembly
- ✓ Generated assembly assembles without errors
- ✓ Data section contains full model binary data

---

### Phase 2: Bootloader Code Generation - Memory Initialization

**Objective**: Generate RISC-V code that loads models from embedded data into correct memory addresses.

**Deliverables**:
- Enhancement to `model_compiler.py`:
  - Add `generate_bootloader_code()` method
  - Generate assembly code that:
    - Copies generator model to 0x10000
    - Copies recognizer model to 0xF4ABC
    - Uses memcpy-like functionality (loop or optimized copy)

**Algorithm**:
```asm
.section .text
_start:
    # Initialize stack pointer
    lui sp, 0x20000
    
    # Copy generator model (memcpy from data section to 0x10000)
    # Load source address (model_data_generator)
    # Load destination (0x10000)
    # Load size (generator size)
    # Loop: lw/sw instructions
    
    # Copy recognizer model to 0xF4ABC
    # Similar loop
    
    # Jump to application entry point
    # (or exit via syscall for testing)
    li a0, 0
    li a7, 93  # exit syscall
    ecall
```

**Unit Tests**:
- Test memcpy code generation
- Test address calculation for each model
- Test size calculations
- Verify loop logic in generated code

**Black Box Tests**:
- Assemble generated bootloader
- Load into emulator
- Run and verify memory at 0x10000 and 0xF4ABC contain correct data
- Verify exit code indicates success

**Exit Criteria**:
- ✓ Bootloader code assembles correctly
- ✓ Models copied to correct memory addresses
- ✓ Memory integrity verified after load
- ✓ Program exits cleanly

---

### Phase 3: Linker Script Configuration - Memory Layout

**Objective**: Create proper linker script that places bootloader code and data at correct addresses.

**Deliverables**:
- `bootloader.ld`: Linker script for bootloader
  - `.text` section: bootloader code at 0x0 (start of memory)
  - `.data` section: embedded model binaries
  - Proper memory regions and constraints

**Linker Script Structure**:
```ld
MEMORY {
    CODE (rx) : ORIGIN = 0x0, LENGTH = 256K      # Code space
    DATA (rw) : ORIGIN = 0x40000, LENGTH = 20M   # Data space
    MODELS (r) : ORIGIN = 0x10000, LENGTH = 10M  # Model memory
}

SECTIONS {
    .text : { *(.text .text.*) } > CODE
    .data : { *(.data .data.*) } > DATA
    .rodata : { *(.rodata .rodata.*) } > DATA
    .bss : { *(.bss .bss.*) } > DATA
}
```

**Unit Tests**:
- Parse linker script
- Verify memory regions are defined
- Check section placement rules

**Black Box Tests**:
- Link bootloader with linker script
- Verify code starts at 0x0
- Verify data placed correctly
- Check ELF structure with readelf/objdump

**Exit Criteria**:
- ✓ Linker script parses correctly
- ✓ Sections placed at expected addresses
- ✓ Generated ELF loads successfully

---

### Phase 4: Model Compiler Integration - Full Pipeline

**Objective**: Integrate all previous phases into a working compiler pipeline.

**Deliverables**:
- `compile_model_bootloader.py`: Complete compiler script
  - Input: JSON intermediate format
  - Output: Assembled bootloader binary (.bin)
  - Single command: `python compile_model_bootloader.py generator.json`

**Pipeline**:
```
JSON → Assembly Generator (Phase 1)
     → Bootloader Code Gen (Phase 2)
     → Combine into .s file
     → RISC-V Assembler
     → RISC-V Linker (with Phase 3 script)
     → Binary Converter (objcopy)
     → Output: bootloader.bin
```

**Unit Tests**:
- Test each pipeline stage
- Test error handling (missing files, invalid JSON)
- Test temporary file cleanup
- Verify output binary format

**Black Box Tests**:
- Generate bootloader from both models
- Load into emulator and run
- Verify memory contents match expected
- Run integration test: bootloader → memory init → app execution

**Exit Criteria**:
- ✓ Complete pipeline works end-to-end
- ✓ Generated bootloader loads and initializes memory correctly
- ✓ Both models placed at correct addresses
- ✓ Data integrity verified

---

### Phase 5: CMake Integration - Automatic Bootloader Generation

**Objective**: Integrate bootloader compilation into CMake build system.

**Deliverables**:
- `cmake/BootloaderBuild.cmake`: CMake helper functions
  - `add_model_bootloader()`: Generate bootloader from JSON
  - Auto-invokes compiler, assembler, linker
  - Outputs to build directory (out-of-tree)

- `CMakeLists.txt` modifications:
  - Add bootloader build rules
  - Generate bootloader targets for each model
  - Integrate into main build

**Unit Tests**:
- Verify CMake functions defined correctly
- Test file discovery
- Test build artifact locations

**Black Box Tests**:
- `cmake ..` and `cmake --build .`
- Verify bootloaders generated in build/
- Load and verify in emulator

**Exit Criteria**:
- ✓ CMake integration complete
- ✓ Bootloaders built automatically
- ✓ Works with clean and incremental builds
- ✓ Out-of-tree structure maintained

---

### Phase 6: Testing & Validation - Unit + Integration Tests

**Objective**: Create comprehensive test suite for bootloader system.

**Deliverables**:
- `test_model_compiler.py`: Unit tests for compiler
  - Test JSON parsing
  - Test assembly generation
  - Test bootloader code generation
  - Test pipeline execution

- `test_bootloader.cpp`: Integration tests
  - Test bootloader loading
  - Verify memory layout
  - Validate model data integrity
  - Performance benchmarks

- `blackbox_tests/bootloader/`: Black box tests
  - RISC-V assembly programs that verify bootloader results
  - Check memory addresses
  - Validate data checksums
  - Measure load time

**Test Coverage**:
- Unit: Compiler logic, assembly generation
- Integration: End-to-end pipeline
- Black Box: RISC-V execution validation

**Exit Criteria**:
- ✓ All unit tests pass
- ✓ All integration tests pass
- ✓ All black box tests pass
- ✓ >90% code coverage
- ✓ Documentation complete

---

### Phase 7: Optimization & Documentation - Polish & Release

**Objective**: Optimize performance, add documentation, prepare for production.

**Deliverables**:
- Performance optimizations:
  - Optimize memcpy implementation (use larger word sizes, unrolled loops)
  - Compress model data (if applicable)
  - Parallel loading (if architecturally possible)

- Documentation:
  - `BOOTLOADER_IMPLEMENTATION.md`: Design and implementation details
  - Code comments and docstrings
  - Usage examples
  - Troubleshooting guide

- Benchmarks:
  - Load time measurements
  - Memory usage analysis
  - Compression ratios

**Exit Criteria**:
- ✓ Load time < target threshold
- ✓ All documentation complete
- ✓ Code reviewed and approved
- ✓ Ready for production use

---

## Testing Strategy

### Unit Tests
- **Location**: `projects/weight-export/test_model_compiler.py`
- **Framework**: pytest
- **Coverage**: 
  - JSON parsing
  - Assembly code generation
  - Bootloader code generation
  - Error handling

### Integration Tests
- **Location**: `projects/emulator/test_bootloader.cpp`
- **Framework**: GTest + Emulator
- **Coverage**:
  - Full pipeline execution
  - Memory initialization
  - Data integrity
  - Performance metrics

### Black Box Tests
- **Location**: `projects/emulator/blackbox_tests/bootloader/`
- **Format**: RISC-V assembly programs
- **Coverage**:
  - Bootloader execution
  - Memory layout verification
  - Model data validation
  - Address correctness

### Continuous Integration
- Tests run on every commit via GitHub Actions
- All three test types must pass
- Performance benchmarks tracked

---

## Dependencies & Prerequisites

### Required
- Python 3.8+
- RISC-V GNU toolchain (riscv64-elf-*)
- CMake 3.10+
- C++17 compiler

### Existing Code
- `model_formats.py`: Intermediate format definition
- `export_generator.py` / `export_recognizer.py`: Model export
- RISC-V emulator (CPU, Memory, Instruction decoder)
- CMake infrastructure

### New Components
- `model_compiler.py`: Core compiler
- `compile_model_bootloader.py`: CLI tool
- Bootloader linker script
- Test suites (unit + integration + black box)

---

## Success Criteria

By the end of Phase 7, we should have:

✓ **Working bootloader system**
- Models embedded in RISC-V binary
- Automatic memory initialization
- No external file loading needed

✓ **Automated compilation pipeline**
- Single command: `python compile_model_bootloader.py model.json`
- CMake integration for automatic building
- Out-of-tree artifacts

✓ **Comprehensive testing**
- Unit tests for compiler logic
- Integration tests for full pipeline
- Black box tests for RISC-V execution
- All tests passing

✓ **Production ready**
- Performance optimized
- Well documented
- Error handling complete
- Code reviewed

---

## Timeline & Effort Estimate

| Phase | Effort | Duration | Blockers |
|-------|--------|----------|----------|
| 1: Compiler | Medium | 2-3 hrs | None |
| 2: Bootloader Code | Medium | 2-3 hrs | Phase 1 |
| 3: Linker Script | Low | 1 hr | Phase 1-2 |
| 4: Integration | Low | 1-2 hrs | Phase 1-3 |
| 5: CMake | Low | 1-2 hrs | Phase 4 |
| 6: Testing | High | 3-4 hrs | Phase 1-5 |
| 7: Polish | Medium | 2-3 hrs | Phase 6 |
| **Total** | **~High** | **~12-18 hrs** | Sequential |

---

## Related Tasks & Deliverables

- Phase 1: Weight Export & Memory Verification ✓ (COMPLETE)
- Phase 2: NEURAL_FC Instruction (future)
- Phase 3: Model Training Integration (future)

This bootloader system enables Phase 2 work by providing efficient model loading without file I/O.

---

## Questions & Decisions

**Open Questions**:
1. Should bootloader remain resident in memory, or transfer control to OS?
2. What's the target load time threshold?
3. Should we support model hot-loading (replacing models at runtime)?
4. Compression? (trade-off between size and decompression time)

**Implementation Decisions** (to confirm):
1. Bootloader exits via syscall (for testing) vs jumps to app entry point
2. Memcpy algorithm: simple loop vs optimized word-copy
3. Error handling: panic syscall vs graceful degradation
4. Bootloader code location: 0x0 vs reserved region

---

## Files to Create/Modify

### New Files
- `projects/weight-export/model_compiler.py` (Phase 1)
- `projects/weight-export/compile_model_bootloader.py` (Phase 4)
- `projects/weight-export/test_model_compiler.py` (Phase 6)
- `projects/emulator/bootloader.ld` (Phase 3)
- `projects/emulator/test_bootloader.cpp` (Phase 6)
- `projects/emulator/blackbox_tests/bootloader/` (Phase 6)
- `projects/emulator/cmake/BootloaderBuild.cmake` (Phase 5)

### Modified Files
- `projects/emulator/CMakeLists.txt` (Phase 5)
- `projects/weight-export/README.md` (Phase 7)
- `projects/emulator/README.md` (Phase 7)

---

## Success Metrics

- ✓ Compiler generates valid RV32I assembly
- ✓ Bootloader loads models in < 100ms
- ✓ Memory integrity verified (checksum match)
- ✓ All 3 test suites pass (unit + integration + black box)
- ✓ Code coverage > 90%
- ✓ Documentation complete and accurate
