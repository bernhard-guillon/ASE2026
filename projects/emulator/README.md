# Emulator and RTL Validation Stack

Main execution backend for ASE2026, combining:

- C++ RV32 emulator (`emulator_runner`)
- Verilator RTL runner (`verilator_runner`)
- neural ISA extension implementation and validation

## Key capabilities

- RV32 execution core + syscall support
- Neural custom instruction execution (`x77` and `x7b` families)
- Differential validation: emulator vs Verilator
- Bootloader/model compiler integration
- Large CTest suite (unit + blackbox + parity + python integration)

## Build and full regression

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
ctest --test-dir build --output-on-failure
```

## Build model ELF targets

```bash
# Character generator baseline
cmake --build build --target neural_elf -j4

# Game movement model (exports JSON + compiles movement.elf)
cmake --build build --target movement_elf -j4

# Game-movement model (j/k input, outputs game-movement.elf)
cmake --build build --target game_movement_elf -j4
```

Generated files:

- `build/neural.elf`
- `build/movement.elf`
- `build/game-movement.elf`

## Useful targeted tests

```bash
ctest --test-dir build -R "^python/verilator/differential_validation$" --output-on-failure
ctest --test-dir build -R "^python/verilator/neural_op_enhance$" --output-on-failure
ctest --test-dir build -R "^parity/" --output-on-failure
```

## PMAC4 run example

```bash
cd build
./verilator_runner ./neural-op-enhance8pmac4.elf --char-code 65 --render-framebuffer
```

Game-movement run example:

```bash
cd build
./emulator_runner ./game-movement.elf --char-code 106 --cycles 12000000 --render-framebuffer --dump-framebuffer
```

Optional GUI mode:

```bash
./verilator_runner ./neural-op-enhance8pmac4.elf --gui --char-code 65
```

## Project structure (high level)

- `CPU.*`, `Memory.*`, `Instruction.*`, `Emulator.*`: core simulator
- `NeuralOps.*`: custom neural operations
- `model_compiler*.py`: model-to-program compiler path
- `blackbox_tests/`: integration and parity tests
- `benchmarks/`: cycle threshold benchmark tooling
- `hdl/`: Verilator/RTL side

## Benchmarks and docs

- Benchmark JSON artifacts:
  - `../../documentation/collected-data/phase*.json`
- Consolidated references:
  - `../../documentation/neural-risc-v-machine.md`
  - `../../documentation/project-log.md`
  - `../../documentation/ase2026.md`
