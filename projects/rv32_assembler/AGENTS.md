# RV32 Assembler

## Overview

Rust-based RISC-V RV32I/F assembler with support for the project's custom neural ISA extensions. Produces ELF binaries consumable by the emulator and Verilator backend.

## Build

```bash
cargo build --release
```

Binary output: `target/release/rv32as`

The CMake build system in `projects/emulator/` automatically builds this as part of the emulator build.

## Usage

```bash
rv32as input.s -o output.bin
```

## Supported Instructions

- **RV32I**: All base integer instructions
- **RV32F**: Single-precision floating-point extensions
- **Custom neural**: `NMATVEC`, `NMATVEC4x`, `NMATVEC8x`, `NVRELU`, `NVRELUX`, `NVSIGPWL`, `NVCLUAMPU8`, PMAC variants

## Key Source Files

| File | Purpose |
|---|---|
| `src/lib.rs` | Core assembler library |
| `src/bin/main.rs` | CLI entry point |
| `src/lexer.rs` | Tokenizer |
| `src/parser.rs` | Instruction parser |
| `src/encoder.rs` | Binary encoding |
| `src/instruction.rs` | Instruction definitions |
| `src/elf_writer.rs` | ELF output generation |
| `src/error.rs` | Error types |

## Testing

```bash
cargo test
```

Parity tests (Rust vs GNU assembler output) are run via CMake in the emulator project:
```bash
ctest --test-dir projects/emulator/build -R parity
```

## Notes

- Edition 2021, dependencies: `anyhow`, `thiserror`
- `test_parity.sh` and `test_fromheredoc.sh` are standalone shell scripts (not part of CI)
- `target/` is gitignored (115 MB build cache)
