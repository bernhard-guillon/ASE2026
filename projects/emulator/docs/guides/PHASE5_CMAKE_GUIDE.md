# Phase 5: CMake Integration Example

This directory demonstrates how to use the Phase 5 CMake bootloader build system.

## Quick Start

The Phase 5 CMake integration (`cmake/BootloaderBuild.cmake`) provides an easy way to compile model bootloaders as part of your CMake build:

```cmake
# Include the bootloader build system
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/BootloaderBuild.cmake)
bootloader_build_system_init()

# Add a model bootloader
add_model_bootloader(generator_bootloader "path/to/generator.json")
add_model_bootloader(recognizer_bootloader "path/to/recognizer.json" BINARY VERBOSE)
```

## What It Does

When you call `add_model_bootloader()`, the CMake system:

1. **Validates** the input JSON file exists
2. **Creates** a build target (e.g., `generator_bootloader`)
3. **Registers** automatic compilation via Phase 4 pipeline:
   - Model Compiler (Phase 1-2)
   - RISC-V Assembler
   - GNU Linker with bootloader.ld
   - Optional binary extraction
4. **Places outputs** in `${CMAKE_BINARY_DIR}/bootloaders/`
5. **Manages dependencies** - rebuilds when JSON changes

## Usage Examples

### Basic: Generate ELF Only

```cmake
add_model_bootloader(generator "models/generator.json")
```

Generates: `build/bootloaders/generator.elf`

### With Binary Output

```cmake
add_model_bootloader(recognizer "models/recognizer.json" BINARY)
```

Generates:
- `build/bootloaders/recognizer.elf`
- `build/bootloaders/recognizer.bin`

### With Verbose Output

```cmake
add_model_bootloader(test_model "test.json" VERBOSE)
```

Shows detailed compilation progress during build.

### Access Outputs in CMake

```cmake
# Get ELF file path
get_bootloader_elf_file(generator_bootloader elf_path)
message(STATUS "Generator ELF: ${elf_path}")

# Get binary file path
get_bootloader_bin_file(generator_bootloader bin_path)

# Get model name
get_bootloader_model_name(generator_bootloader model_name)
message(STATUS "Model: ${model_name}")
```

## Building

```bash
# Create build directory
mkdir build
cd build

# Configure
cmake ..

# Build all bootloaders
cmake --build . --target all

# Build specific bootloader
cmake --build . --target generator_bootloader

# Run tests including Phase 5
ctest
```

## Output Structure

```
build/
├── bootloaders/          # Out-of-tree artifacts
│   ├── generator.elf
│   ├── generator.bin     (optional)
│   ├── recognizer.elf
│   └── recognizer.bin    (optional)
└── ...
```

## Features

- ✅ **Single-command compilation** - replaces 4 manual steps
- ✅ **Automatic tool detection** - finds RISC-V toolchain
- ✅ **Dependency tracking** - rebuilds when JSON changes
- ✅ **Out-of-tree builds** - keeps source directory clean
- ✅ **Error handling** - clear messages if tools missing
- ✅ **CMake integration** - works with other build targets
- ✅ **Optional binary output** - generate .bin files as needed

## How It Works (Behind the Scenes)

The CMake module (`cmake/BootloaderBuild.cmake`) wraps the Phase 4 pipeline script:

```
Model JSON
    ↓
Model Compiler (Phase 1-2)  [model_compiler.py]
    ↓
RISC-V Assembler            [riscv64-elf-as]
    ↓
Linker with bootloader.ld   [riscv64-elf-ld]
    ↓
ELF Binary
    ↓
(Optional) Binary Extraction [riscv64-elf-objcopy]
    ↓
Raw Binary
```

All of this is orchestrated by the Phase 4 wrapper (`compile_model_bootloader.py`), which the CMake module automatically invokes.

## For More Information

- **Phase 1-2**: See `model_compiler.py`
- **Phase 3**: See `bootloader.ld`
- **Phase 4**: See `compile_model_bootloader.py`
- **Phase 5**: See `cmake/BootloaderBuild.cmake`
- **Tests**: See `test_bootloader_phase5.py`
