# RV32I Emulator Plan (C++ + Unit Tests)

## Problem Statement
Build a simple, testable RV32I emulator in C++ that can run a minimal "Hello World" program using Linux-style `ecall` handling (`write` and `exit`).

## Proposed Approach
Keep architecture modular and incremental so each phase is independently testable:

- CPU state (`x0..x31`, `pc`)
- Memory abstraction
- Decoder + executor
- Syscall handler
- Emulator run loop and binary loading

We will deliver in 7 phases, each with code + tests before moving to the next phase.

## 7 Phases

### Phase 1: Memory Module
Deliver:
- `Memory` class with `read8`, `write8`, `read32`, `write32`
- Bounds checking and alignment behavior definition
- Unit tests for valid and invalid accesses

Exit criteria:
- Memory read/write behavior is deterministic and fully covered by tests.

### Phase 2: CPU State
Deliver:
- `CPUState` with 32 registers and `pc`
- `x0` hardwired to zero
- Accessor/mutator methods and reset behavior
- Unit tests for register semantics and PC updates

Exit criteria:
- Register and PC invariants enforced in tests.

### Phase 3: Instruction Decoder
Deliver:
- Instruction field extraction utilities
- Decoding for R/I/S/B/U/J formats as needed by RV32I subset rollout
- Unit tests with known instruction encodings

Exit criteria:
- Decoder outputs expected fields for representative instructions.

### Phase 4: ALU + Basic Execution
Deliver:
- Execute core arithmetic/logic instructions:
  - `ADD`, `SUB`, `AND`, `OR`, `XOR`, `SLL`, `SRL`, `SRA`
  - Immediate forms (at least `ADDI`, then extend as needed)
- Unit tests for each operation including edge values

Exit criteria:
- Instruction execution updates destination registers correctly and preserves `x0`.

### Phase 5: Load/Store + Branches
Deliver:
- `LW`, `SW`
- Branches: `BEQ`, `BNE`, `BLT`, `BGE`
- Proper branch target and PC update semantics
- Unit tests for taken/not-taken behavior and memory effects

Exit criteria:
- Memory + control-flow instructions behave per RV32I semantics in tests.

### Phase 6: Jumps + Remaining Immediate/Control Ops
Deliver:
- `JAL`, `JALR`
- Remaining immediate operations needed for small programs
- Any missing control-flow pieces for assembly test programs
- Unit tests for link register values and target computation

Exit criteria:
- Emulator can run non-trivial control flow without syscall support yet.

### Phase 7: Syscalls + Integration
Deliver:
- `ecall` handling with minimal syscall surface:
  - `write` (64)
  - `exit` (93)
- Simple binary/program loader path for assembled test program
- Integration tests that validate output and exit behavior

Exit criteria:
- End-to-end "Hello World" program runs in emulator.

## Work Breakdown Notes
- Use existing RISC-V toolchain (`riscv32-unknown-elf-as`, `ld`) to assemble/link test programs.
- Avoid writing a custom assembler in this scope.
- Prioritize correctness and testability over performance.
- Keep component interfaces small to simplify later extension (e.g., `M`, `C`, privileged modes).

## Assumptions
- Build system and test framework are available or will be set up early (prefer CMake + GoogleTest).
- Initial target is interpreter-style execution (no JIT/dynarec).
- Flat memory model is sufficient for first milestone.

## Definition of Done
- All 7 phases completed with passing unit/integration tests.
- Able to run and validate a minimal "Hello World" RV32I program through emulator runtime.
