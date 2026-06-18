# Build Directory Usage Guide

## Important Note

**Always use `build` directory for building and running.**

The build directory is `projects/emulator/build/`. All documentation and tests reference this path.

## Standard Workflow

```bash
# 1. Configure (only needed once or when CMakeLists.txt changes)
cd projects/emulator
cmake -B build

# 2. Build
cmake --build build -j$(nproc)

# 3. Run
./build/emulator_runner build/squash.elf --cycles 1000000
```

## Key Files

- **ELF binaries**: `build/*.elf`
- **Emulator runner**: `build/emulator_runner`
- **Verilator runner**: `build/verilator_runner`

## Common Commands

```bash
# Run emulator (software simulation)
./build/emulator_runner build/squash.elf --char-code 0 --cycles 1000000

# Run verilator (hardware simulation)
./build/verilator_runner build/squash.elf --char-code 0 --cycles 1000000

# Run GUI mode
./build/emulator_runner build/squash.elf --gui
```

## Troubleshooting

If you get errors about missing files:
1. Make sure you're in the project root directory
2. Make sure you've built the targets first
3. Never manually create or delete files in build - let CMake manage it
