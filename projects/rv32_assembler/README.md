# RV32 Assembler - Phase C Foundation

A minimal RISC-V RV32I + RV32F assembler written in Rust, designed for correctness-first baseline parity testing against the GNU assembler.

## Scope (Phase C)

- **Instruction set**: RV32I + RV32F (no neural ops yet - those are Phase D)
- **Output format**: Raw binary (`.o` object files with just `.text` section)
- **Features**: Tokenizer, parser, instruction encoder
- **No**: Labels, symbols, directives, linker, ELF headers, relocations

## Architecture

### Modules

1. **lexer.rs**: Tokenize assembly source
   - Handles mnemonics, registers (x0-x31), float registers (f0-f31), integers, parentheses
   - Strips comments
   - Special handling for `xor` (not to be confused with `x0`-`x31` registers)

2. **instruction.rs**: IR representation
   - Register/FloatRegister enums with name parsing (x1, sp, a0, etc.)
   - 13 instruction type variants (RType, IType, SType, BType, UType, JType, FRType, FIType, FSType, FCType, FCvtType, FCvtRevType, FMoveType, FMoveRevType)

3. **parser.rs**: Convert tokens to instructions
   - Instruction-specific parsing with proper token count validation
   - Special handling for load/store (offset(register) syntax)
   - Proper error messages for wrong operand counts

4. **encoder.rs**: Convert instructions to 32-bit machine code
   - RISC-V opcode/funct field encoding
   - Immediate value range validation
   - Bit-packing for all instruction formats
   - 100% deterministic output

5. **lib.rs**: Public API
   - `assemble_instruction(line)` → 4 bytes
   - `assemble_program(text)` → Vec<u8>

6. **bin/main.rs**: CLI tool `rv32as`
   - Usage: `rv32as input.s [-o output.o]`
   - Writes raw binary to file

## Supported Instructions

### RV32I (Integer)

#### R-type (register-register)
- `add`, `sub`, `and`, `or`, `xor`, `sll`, `srl`, `sra`

#### I-type (immediate)
- Arithmetic: `addi`, `andi`, `ori`, `xori`, `slli`, `srli`, `srai`
- Load: `lw`, `lh`, `lb`, `lwu`, `lhu`
- Jump: `jalr`

#### S-type (store)
- `sw`, `sh`, `sb`

#### B-type (branch)
- `beq`, `bne`, `blt`, `bltu`, `bge`, `bgeu`

#### U-type (upper immediate)
- `lui`, `auipc`

#### J-type (jump)
- `jal`

### RV32F (Floating-Point)

#### FR-type (register-register)
- `fadd.s`, `fsub.s`, `fmul.s`, `fdiv.s`

#### FI-type (load)
- `flw` (load float from memory)

#### FS-type (store)
- `fsw` (store float to memory)

#### FC-type (compare)
- `feq.s`, `flt.s`, `fle.s`

#### FCVT/FMV (conversions)
- `fcvt.w.s` (float to int)
- `fcvt.s.w` (int to float)
- `fmv.x.w` (float reg to int reg)
- `fmv.w.x` (int reg to float reg)

## Usage

### Assemble a file

```bash
rv32as program.s -o program.o
```

### Programmatic API

```rust
use rv32_assembler::assemble_program;

let asm = r#"
    addi x1, x0, 42
    add x2, x1, x1
"#;

let bytes = assemble_program(asm)?;
assert_eq!(bytes.len(), 8); // 2 instructions
```

## Testing

### Unit tests (17 passing)

```bash
cargo test
```

Tests cover:
- Register/float register parsing
- Tokenization (mnemonics, immediate values, parentheses)
- Parsing all instruction types
- Encoding (opcodes, field values, immediate ranges)
- Roundtrip: token → instruction → bytes

### Blackbox tests

Compare output against GNU assembler:

```bash
# Assemble with both
riscv64-elf-as -march=rv32if -mabi=ilp32f program.s -o gnu.o
rv32as program.s -o rust.o

# Extract and compare .text sections
objcopy -O binary -j .text gnu.o gnu.bin
objcopy -O binary -j .text rust.o rust.bin
diff gnu.bin rust.bin
```

## Known Limitations (Phase C)

- No label or symbol resolution (labels are not parsed as tokens)
- No directives (.text, .data, .section, etc.)
- No pseudo-instructions (e.g., `li` as pseudo for `addi`/`lui`)
- Immediate values must be in range for the instruction type
- No relocations or linking
- Binary output only (no ELF headers)
- Comments must start with `#` and extend to end of line

## Error Handling

Errors are returned as `AssemblerError`:
- `LexerError` - Invalid token
- `ParserError` - Unexpected token sequence
- `UnknownInstruction` - Mnemonic not recognized
- `InvalidRegister` - Register name not recognized
- `InvalidImmediate` - Value out of range
- `WrongOperandCount` - Instruction has wrong number of operands

## Example Assembly

```asm
# Load constant into x1
addi x1, x0, 42

# Add two registers
add x2, x1, x1

# Load from memory
lw x3, 0(x2)

# Store to memory
sw x1, 4(x2)

# Floating-point
fadd.s f1, f2, f3

# Convert and move
fcvt.s.w f4, x4
```

## Performance

- Single-pass assembly (lexer → parser → encoder)
- No optimization or peephole passes
- ~100 KB/s assembly rate on typical hardware

## Next Steps (Phase D)

- Add new neural op instructions (NMATVEC.F32, NVRELU.F32, etc.)
- Implement instruction encoding for new opcodes
- Create blackbox parity tests for new instructions
- Add optimization and SIMD instruction support

## Toolchain

- **Rust**: 1.70+
- **Dependencies**: `thiserror`, `anyhow`
- **Minimum Supported**: no platform-specific code, portable

## File Structure

```
rv32_assembler/
├── Cargo.toml
├── src/
│   ├── lib.rs          # Public API
│   ├── error.rs        # Error types
│   ├── instruction.rs  # IR and register definitions
│   ├── lexer.rs        # Tokenizer
│   ├── parser.rs       # Token → Instruction
│   ├── encoder.rs      # Instruction → bytes
│   └── bin/
│       └── main.rs     # CLI tool
└── test-asm/           # Example assembly files
```
