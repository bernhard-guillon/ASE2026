# Using the C Model Compiler

The C Model Compiler (`model_compiler_to_C.py`) generates C files with embedded RISC-V assembly that can be compiled with `riscv64-elf-gcc`. This allows neural network models to be integrated into C-based toolchains while maintaining the same functionality as the original assembly-based compiler.

## Overview

The C Model Compiler:
- Converts JSON intermediate format models to C source files
- Embeds model data (weights, biases) as `const uint32_t` arrays
- Wraps RISC-V assembly functions in C functions using `__asm__ volatile` blocks
- Generates proper symbol definitions for model data access

## Files

- `model_compiler_to_C.py` - Main C compiler script
- `riscv_generator.ld` - Linker script for generator models (places data at 0x10000)
- `riscv_flat.ld` - Linker script for flat memory layout (everything at 0x0)

## Usage

### Step 1: Generate C File

```bash
cd projects/emulator
python3 model_compiler_to_C.py <model.json> -o output.c [-v]
```

Options:
- `-o output.c` - Output C file path (default: `<model.json>.c`)
- `-v` - Verbose output

### Step 2: Compile to ELF

For **generator models** (recommended):
```bash
riscv64-elf-gcc -march=rv32if -mabi=ilp32f -nostdlib \
  -T riscv_generator.ld -Wl,--oformat=elf32-littleriscv \
  -o output.elf output.c
```

For **flat memory layout** (code and data at address 0):
```bash
riscv64-elf-gcc -march=rv32if -mabi=ilp32f -nostdlib \
  -T riscv_flat.ld -Wl,--oformat=elf32-littleriscv \
  -o output.elf output.c
```

### Step 3: Run with Emulator

```bash
./build/emulator_runner output.elf --dump-framebuffer --cycles 20000000 --char a
```

## Python API

### Basic Compilation

```python
from model_compiler_to_C import CModelCompiler

compiler = CModelCompiler(verbose=True)
compiler.compile('build/model.json', 'output.c')
```

### Direct ELF Compilation

```python
from model_compiler_to_C import CModelCompiler

compiler = CModelCompiler()
elf_path = compiler.compile_to_elf('build/model.json', 'output.elf')
```

### With Custom Linker Script

```python
compiler = CModelCompiler()
elf_path = compiler.compile_to_elf(
    'build/model.json', 
    'output.elf',
    linker_script='riscv_generator.ld'
)
```

## Memory Layout

The C compiler uses the same memory layout as the original assembly compiler:

| Address Range | Purpose |
|---------------|---------|
| 0x00000000 | Code execution |
| 0x00010000 | Model data (weights, biases) |
| 0x00150000 | Input buffer |
| 0x00151000 | Activation buffer A |
| 0x00152000 | Activation buffer B |
| 0x00153000 | Output buffer |
| 0x00020000 | Framebuffer (20x20 pixels) |

## Model Types

The compiler supports:
- `generator` models - Character generators with counter feedback
- `block-diagonal-parallel` architecture - Combined counter+chargen networks

## Key Implementation Details

### Model Data Embedding
Model data is embedded as a C array:
```c
const uint32_t model_data[N] __attribute__((aligned(4))) = {
    0x4E52414EU,  // Magic number "NRAL"
    0x00000001U,  // Version
    // ... weights and biases
};
```

### Symbol Definitions
The compiler creates assembly directives to alias symbols:
```c
__asm__(".section .rodata\n"
       ".globl model_data_start\n"
       ".set model_data_start, model_data\n"
       ".globl model_data_end\n"
       ".set model_data_end, model_data + N\n"
       ".previous\n");
```

This ensures `la s0, model_data_start` in the assembly code resolves to the correct address.

### Function Wrapping
Each assembly function is wrapped in a C function:
```c
void layer_0_forward(void) {
    __asm__ volatile (
        "addi sp, sp, -32\n"
        "sw ra, 28(sp)\n"
        "...\n"
    );
}
```

## Troubleshooting

### "Unsupported opcode in execute"
This error occurs when the ELF uses instructions not supported by the emulator. Ensure:
- Compiler uses `-march=rv32if` (F extension for float support)
- Emulator supports the F extension

### All-zero framebuffer output
The model may need more execution cycles. Try increasing `--cycles` to 20000000 or more.

### "Memory access out of bounds"
This typically means the code is accessing memory outside the emulator's address space. Check:
- Linker script places data at correct addresses
- Model data offsets are calculated correctly

## Differences from Assembly Compiler

1. **Code Wrapping**: Assembly functions are wrapped in C functions with prologue/epilogue
2. **Symbol Resolution**: GCC resolves `la` pseudo-instructions at compile time using absolute addresses
3. **Memory Layout**: Uses linker scripts to control data placement
4. **Entry Point**: Generates `_start()` function instead of relying on ELF entry point

## Example: Full Pipeline

```bash
# 1. Export model to JSON
python3 export_counter255_three_layer.py

# 2. Compile to C
python3 model_compiler_to_C.py build/model.json -o model.c -v

# 3. Compile C to ELF
riscv64-elf-gcc -march=rv32if -mabi=ilp32f -nostdlib \
  -T riscv_generator.ld -Wl,--oformat=elf32-littleriscv \
  -o model.elf model.c

# 4. Test with emulator
./build/emulator_runner model.elf --dump-framebuffer --cycles 20000000 --char a
```

## Compatibility

- **RISC-V Toolchain**: Requires `riscv64-elf-gcc` with F extension support
- **Architecture**: `rv32if` (32-bit, integer + float)
- **ABI**: `ilp32f` (32-bit integers, float registers)
- **Output Format**: `elf32-littleriscv`
