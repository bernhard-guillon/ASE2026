# rv32as — Custom RV32 Assembler

Rust assembler used in ASE2026 for RV32I/RV32F plus project neural custom instructions.

## Scope

- Core ISA: RV32I + RV32F
- Project ISA extensions:
  - `nmatvec.f32`, `nvrelu.f32`, `nvsigpwl.f32`, `nvclampu8.f32`
  - x7b family: `nmatvecx.f32`, `nmatvec4x.f32`, `nmatvec8x.f32`,
    `nmatvec8xp.f32`, `nmatvec8xp2.f32`, `nmatvec8xp3.f32`, `nmatvec8xp4.f32`

## Build

```bash
cargo build --release --bin rv32as
```

## Usage

```bash
./target/release/rv32as input.s -o output.o
```

Supported GNU-style pass-through flags:
- `-march ...`
- `-mabi ...`
- `-o ...`

## Tests

```bash
cargo test
./test_parity.sh
```

`test_parity.sh` compares encoded output against GNU assembler flows for parity checks.

## Integration

`projects/emulator/CMakeLists.txt` builds `rv32as` via Cargo and wires it into parity/fixture testing.
