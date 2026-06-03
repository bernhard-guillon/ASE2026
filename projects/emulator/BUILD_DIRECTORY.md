# Build Directory Usage Guide

## Important Note

**Always use `build_cmake` directory for building and running.**

Do NOT toggle between `build` and `build_cmake` directories. The project is configured to use `build_cmake` exclusively.

## Standard Workflow

```bash
# 1. Configure (only needed once or when CMakeLists.txt changes)
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
mkdir -p build_cmake
cd build_cmake
cmake ..

# 2. Build (from project root)
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator
cmake --build build_cmake

# 3. Run
./build_cmake/emulator_runner build_cmake/squash.elf --cycles 1000000
./build_cmake/verilator_runner build_cmake/squash.elf --cycles 1000000
```

## Key Files

- **ELF binary**: `build_cmake/squash.elf`
- **Emulator runner**: `build_cmake/emulator_runner`
- **Verilator runner**: `build_cmake/verilator_runner`

## Common Commands

```bash
# Run emulator (software simulation)
./build_cmake/emulator_runner build_cmake/squash.elf --char-code 0 --cycles 1000000

# Run verilator (hardware simulation)
./build_cmake/verilator_runner build_cmake/squash.elf --char-code 0 --cycles 1000000

# Run GUI mode
./build_cmake/emulator_runner build_cmake/squash.elf --gui
```

## Troubleshooting

If you get errors about missing files:
1. Make sure you're in the project root directory
2. Make sure you've built the targets first
3. Never manually create or delete files in build_cmake - let CMake manage it