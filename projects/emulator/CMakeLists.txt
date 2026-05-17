cmake_minimum_required(VERSION 3.14)
project(RV32I_Emulator)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Fetch GoogleTest
include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Enable testing
enable_testing()

# Phase 5: Include bootloader build system (Phase 4 wrapper automation)
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/BootloaderBuild.cmake)
bootloader_build_system_init()

# ============================================================================
# Phase C: Build Rust assembler (RV32I/F parity baseline)
# ============================================================================

find_program(CARGO cargo)
if(CARGO)
    message(STATUS "Cargo found: ${CARGO}")
    
    # Build Rust assembler
    set(RUST_ASSEMBLER_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../rv32_assembler)
    set(RUST_ASSEMBLER_BIN ${CMAKE_CURRENT_BINARY_DIR}/rv32as)
    
    add_custom_command(
        OUTPUT ${RUST_ASSEMBLER_BIN}
        COMMAND ${CARGO} build --quiet --release --bin rv32as
        WORKING_DIRECTORY ${RUST_ASSEMBLER_DIR}
        COMMAND ${CMAKE_COMMAND} -E copy
            ${RUST_ASSEMBLER_DIR}/target/release/rv32as
            ${RUST_ASSEMBLER_BIN}
        DEPENDS
            ${RUST_ASSEMBLER_DIR}/src/lib.rs
            ${RUST_ASSEMBLER_DIR}/src/bin/main.rs
            ${RUST_ASSEMBLER_DIR}/src/lexer.rs
            ${RUST_ASSEMBLER_DIR}/src/parser.rs
            ${RUST_ASSEMBLER_DIR}/src/encoder.rs
            ${RUST_ASSEMBLER_DIR}/src/instruction.rs
            ${RUST_ASSEMBLER_DIR}/src/error.rs
            ${RUST_ASSEMBLER_DIR}/Cargo.toml
        COMMENT "Building Rust assembler (rv32as)"
        VERBATIM
    )
    
    add_custom_target(rv32as_build ALL DEPENDS ${RUST_ASSEMBLER_BIN})
    set(RV32AS_EXECUTABLE ${RUST_ASSEMBLER_BIN})
else()
    message(WARNING "Cargo not found - Rust assembler will not be built")
    set(RV32AS_EXECUTABLE "")
endif()


# Memory module
add_library(memory Memory.cpp)

# CPU module
add_library(cpu CPU.cpp)
target_link_libraries(cpu memory instruction neural_ops)

# Instruction decoder module
add_library(instruction Instruction.cpp)

# Neural ops module (Phase B foundation)
add_library(neural_ops NeuralOps.cpp)

# Emulator module
add_library(emulator Emulator.cpp)
target_link_libraries(emulator cpu memory instruction neural_ops)

# Unit test include directory (tests moved to utest/ subdirectory)
set(UNIT_TEST_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR})

# Memory tests
add_executable(test_memory utest/test_memory.cpp)
target_include_directories(test_memory PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_memory memory gtest_main)

# CPU tests
add_executable(test_cpu utest/test_cpu.cpp)
target_include_directories(test_cpu PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_cpu cpu gtest_main)

# Instruction decoder tests
add_executable(test_instruction utest/test_instruction.cpp)
target_include_directories(test_instruction PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_instruction instruction gtest_main)

# Execution tests
add_executable(test_execution utest/test_execution.cpp)
target_include_directories(test_execution PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_execution cpu memory instruction gtest_main)

# Emulator integration tests
add_executable(test_emulator utest/test_emulator.cpp)
target_include_directories(test_emulator PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_emulator emulator cpu memory instruction gtest_main)

# File I/O syscall tests
add_executable(test_file_io_syscalls utest/test_file_io_syscalls.cpp)
target_include_directories(test_file_io_syscalls PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_file_io_syscalls emulator cpu memory instruction gtest_main)

# Memory syscall tests
add_executable(test_memory_syscalls utest/test_memory_syscalls.cpp)
target_include_directories(test_memory_syscalls PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_memory_syscalls emulator cpu memory instruction gtest_main)

# Instruction edge case tests
add_executable(test_instruction_edges utest/test_instruction_edges.cpp)
target_include_directories(test_instruction_edges PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_instruction_edges cpu memory instruction gtest_main)

# Framebuffer tests
add_executable(test_framebuffer utest/test_framebuffer.cpp)
target_include_directories(test_framebuffer PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_framebuffer emulator cpu memory instruction gtest_main)

# ELF Loader tests
add_executable(test_elf_loader utest/test_elf_loader.cpp)
target_include_directories(test_elf_loader PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_elf_loader emulator cpu memory instruction gtest_main)

# Model loading tests
add_executable(test_model_loading utest/test_model_loading.cpp)
target_include_directories(test_model_loading PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_model_loading emulator cpu memory instruction)

# Floating-point instruction tests (F extension)
add_executable(test_fp_instructions utest/test_fp_instructions.cpp)
target_include_directories(test_fp_instructions PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_fp_instructions emulator cpu memory instruction gtest_main)

# Neural ops unit tests (Phase B foundation)
add_executable(test_neural_ops utest/test_neural_ops.cpp)
target_include_directories(test_neural_ops PRIVATE ${UNIT_TEST_INCLUDE_DIR})
target_link_libraries(test_neural_ops neural_ops gtest_main)

# RISC-V memory layout test runner
add_executable(run_memory_layout_test blackbox_tests/neural_network/run_memory_layout_test.cpp)
target_link_libraries(run_memory_layout_test emulator cpu memory instruction)

# Binary loader and runner
add_executable(emulator_runner emulator_runner.cpp)
target_link_libraries(emulator_runner emulator cpu memory instruction)

# Register tests with CTest
include(GoogleTest)
gtest_discover_tests(test_memory)
gtest_discover_tests(test_cpu)
gtest_discover_tests(test_instruction)
gtest_discover_tests(test_execution)
gtest_discover_tests(test_emulator)
gtest_discover_tests(test_file_io_syscalls)
gtest_discover_tests(test_fp_instructions)
gtest_discover_tests(test_memory_syscalls)
gtest_discover_tests(test_instruction_edges)
gtest_discover_tests(test_framebuffer)
gtest_discover_tests(test_elf_loader)
gtest_discover_tests(test_neural_ops)

# Register integration tests
add_test(NAME test_model_loading COMMAND test_model_loading)
add_test(NAME test_memory_layout COMMAND run_memory_layout_test)

# ============================================================================
# Blackbox Testing
# ============================================================================

# Find RISC-V toolchain (support both Arch Linux riscv64-elf-* and Ubuntu riscv64-unknown-elf-* naming)
find_program(RISCV_GCC    NAMES riscv64-elf-gcc    riscv64-unknown-elf-gcc)
find_program(RISCV_AS     NAMES riscv64-elf-as     riscv64-unknown-elf-as)
find_program(RISCV_LD     NAMES riscv64-elf-ld     riscv64-unknown-elf-ld)
find_program(RISCV_OBJCOPY NAMES riscv64-elf-objcopy riscv64-unknown-elf-objcopy)

if(RISCV_GCC AND RISCV_AS AND RISCV_LD AND RISCV_OBJCOPY)
    set(RISCV_TOOLCHAIN_FOUND TRUE)
    message(STATUS "RISC-V toolchain found")
    message(STATUS "  GCC: ${RISCV_GCC}")
    message(STATUS "  AS:  ${RISCV_AS}")
    message(STATUS "  LD:  ${RISCV_LD}")
    message(STATUS "  OBJCOPY: ${RISCV_OBJCOPY}")
else()
    set(RISCV_TOOLCHAIN_FOUND FALSE)
    message(WARNING "RISC-V toolchain not found - blackbox tests disabled")
    if(NOT RISCV_GCC)
        message(WARNING "  Missing: riscv64-elf-gcc / riscv64-unknown-elf-gcc")
    endif()
    if(NOT RISCV_AS)
        message(WARNING "  Missing: riscv64-elf-as / riscv64-unknown-elf-as")
    endif()
    if(NOT RISCV_LD)
        message(WARNING "  Missing: riscv64-elf-ld / riscv64-unknown-elf-ld")
    endif()
    if(NOT RISCV_OBJCOPY)
        message(WARNING "  Missing: riscv64-elf-objcopy / riscv64-unknown-elf-objcopy")
    endif()
endif()

# ============================================================================
# Python Bootloader Tests (Phase 1-3)
# ============================================================================

# Find Python
find_program(PYTHON_EXECUTABLE python3)
if(PYTHON_EXECUTABLE)
    message(STATUS "Python found: ${PYTHON_EXECUTABLE}")
    
    # Phase 1: Model Compiler Tests (no toolchain needed)
    add_test(
        NAME python/phase1/model_compiler_unit
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_model_compiler.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase1/model_compiler_blackbox
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_model_compiler_blackbox.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 2: Bootloader Code Generation Tests (no toolchain needed)
    add_test(
        NAME python/phase2/bootloader_unit
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase2.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase2/bootloader_blackbox
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase2_blackbox.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 3: Linker Script Configuration Tests (requires RISC-V toolchain)
    add_test(
        NAME python/phase3/linker_script_unit
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase3.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase3/linker_script_blackbox
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase3_blackbox.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase3/linker_script_integration
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase3_integration.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 4: Full Pipeline Integration Tests (requires RISC-V toolchain)
    add_test(
        NAME python/phase4/pipeline_integration
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase4_integration.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    message(STATUS "Phase 3-4 Python tests registered")
    
    # Phase 5: CMake Build System Tests (no toolchain needed)
    add_test(
        NAME python/phase5/cmake_build_system
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase5.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 6: Comprehensive Integration Tests (requires RISC-V toolchain)
    add_test(
        NAME python/phase6/comprehensive_integration
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_bootloader_phase6_integration.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    message(STATUS "Phase 6 Python tests registered")
    
    # Static Character Generation Tests
    add_test(
        NAME python/static_char_gen/integration
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_static_char_gen_integration.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/static_char_gen/basic
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_static_char_gen_basic.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # Game movement replay test (packed a0 input mapping)
    add_test(
        NAME python/game_movement/replay_subset
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_game_movement_replay.py -k replay_subset -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # Game movement readiness gate (determinism, border safety, repeated-loop stability)
    add_test(
        NAME python/game_movement/readiness_gate
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_game_movement_replay.py -k readiness_gate -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/game_movement/squash_elf_smoke
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_game_movement_elf_smoke.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/game_movement/chained_elf_smoke
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_chained_model_elf_smoke.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/counter_char/scaffold_elf_smoke
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_counter_char_elf_scaffold.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/counter255/runtime_smoke
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_counter255_runtime_smoke.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/counter_char/combined_elf_smoke
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_counter_char_combined_smoke.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    add_test(
        NAME python/counter_char/combined_elf_blackbox
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_counter_char_combined_blackbox.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
     
    # ELF Loader Tests
    add_test(
        NAME python/elf_loader/blackbox
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_elf_loader_blackbox.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # Neural ops oracle semantics tests (Phase A foundation)
    add_test(
        NAME python/neural_ops/oracle
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_neural_ops_oracle.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # Drop-in assembler parity scaffold (opt-in via EMULATOR_NEW_ASSEMBLER)
    add_test(
        NAME python/assembler/dropin_parity_scaffold
        COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_assembler_dropin_parity_scaffold.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # Neural instruction assembler blackbox tests (requires rv32as)
    if(RV32AS_EXECUTABLE)
        add_test(
            NAME python/assembler/neural_instr_encoding
            COMMAND ${PYTHON_EXECUTABLE} -m pytest blackbox_tests/test_neural_instr_assembler.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        set_tests_properties(python/assembler/neural_instr_encoding PROPERTIES
            LABELS "assembler;neural;blackbox"
            ENVIRONMENT "EMULATOR_NEW_ASSEMBLER=${RV32AS_EXECUTABLE}"
        )
    else()
        message(WARNING "rv32as not available - python/assembler/neural_instr_encoding test disabled")
    endif()
    
else()
    message(WARNING "Python3 not found - Python tests will be skipped")
endif()

if(RISCV_TOOLCHAIN_FOUND)
    # Include blackbox testing functions
    include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/BlackboxTests.cmake)
    
    # Discover and register all assembly tests
    add_blackbox_asm_tests()
    
    # Discover and register all C tests
    add_blackbox_c_tests()
    
    # Build neural network RISC-V test program
    add_neural_network_test()
    
    # Build ELF loader test programs for Python blackbox tests
    add_elf_loader_test_programs()

    # Make the C++ ELF loader test depend on the compiled ELF files
    add_dependencies(test_elf_loader elf_loader_tests)

    # Pass the ELF loader build directory to the C++ test so loadFile() can find the files
    target_compile_definitions(test_elf_loader PRIVATE
        ELF_LOADER_BUILD_DIR="${CMAKE_CURRENT_BINARY_DIR}/elf_loader_tests"
    )

    # Build static_char_gen.elf for the Python integration tests
    set(STATIC_CHAR_GEN_ELF "${CMAKE_CURRENT_BINARY_DIR}/static_char_gen.elf")
    add_custom_command(
        OUTPUT ${STATIC_CHAR_GEN_ELF}
        COMMAND ${RISCV_GCC} -march=rv32i -mabi=ilp32 -nostdlib -static
            -I${CMAKE_CURRENT_SOURCE_DIR}
            -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            -o ${STATIC_CHAR_GEN_ELF}
            ${CMAKE_CURRENT_SOURCE_DIR}/crt0.s
            ${CMAKE_CURRENT_SOURCE_DIR}/syscalls.s
            ${CMAKE_CURRENT_SOURCE_DIR}/static_char_gen.c
        DEPENDS
            ${CMAKE_CURRENT_SOURCE_DIR}/static_char_gen.c
            ${CMAKE_CURRENT_SOURCE_DIR}/character_font.h
            ${CMAKE_CURRENT_SOURCE_DIR}/crt0.s
            ${CMAKE_CURRENT_SOURCE_DIR}/syscalls.s
            ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
        COMMENT "Compiling static_char_gen.elf"
        VERBATIM
    )
    add_custom_target(static_char_gen_elf ALL DEPENDS ${STATIC_CHAR_GEN_ELF})

    # Build neural.elf from model JSON for GUI/differential Verilator smoke tests
    if(PYTHON_EXECUTABLE)
        set(NEURAL_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural.s")
        set(NEURAL_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural.o")
        set(NEURAL_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural.elf")
        set(NEURAL_OPSX77_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-ai-opsx77.s")
        set(NEURAL_OPSX77_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-ai-opsx77.o")
        set(NEURAL_OPSX77_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-ai-opsx77.elf")
        set(NEURAL_OPSX77_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-ai-opsx77.bin")
        set(NEURAL_OP_ENHANCE_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance.s")
        set(NEURAL_OP_ENHANCE_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance.o")
        set(NEURAL_OP_ENHANCE_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance.elf")
        set(NEURAL_OP_ENHANCE_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance.bin")
        set(NEURAL_OP_ENHANCE4_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance4.s")
        set(NEURAL_OP_ENHANCE4_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance4.o")
        set(NEURAL_OP_ENHANCE4_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance4.elf")
        set(NEURAL_OP_ENHANCE4_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance4.bin")
        set(NEURAL_OP_ENHANCE8_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8.s")
        set(NEURAL_OP_ENHANCE8_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8.o")
        set(NEURAL_OP_ENHANCE8_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8.elf")
        set(NEURAL_OP_ENHANCE8_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8.bin")
        set(NEURAL_OP_ENHANCE8PMAC_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac.s")
        set(NEURAL_OP_ENHANCE8PMAC_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac.o")
        set(NEURAL_OP_ENHANCE8PMAC_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac.elf")
        set(NEURAL_OP_ENHANCE8PMAC_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac.bin")
        set(NEURAL_OP_ENHANCE8PMAC2_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac2.s")
        set(NEURAL_OP_ENHANCE8PMAC2_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac2.o")
        set(NEURAL_OP_ENHANCE8PMAC2_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac2.elf")
        set(NEURAL_OP_ENHANCE8PMAC2_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac2.bin")
        set(NEURAL_OP_ENHANCE8PMAC3_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac3.s")
        set(NEURAL_OP_ENHANCE8PMAC3_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac3.o")
        set(NEURAL_OP_ENHANCE8PMAC3_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac3.elf")
        set(NEURAL_OP_ENHANCE8PMAC3_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac3.bin")
        set(NEURAL_OP_ENHANCE8PMAC4_ASM "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac4.s")
        set(NEURAL_OP_ENHANCE8PMAC4_OBJ "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac4.o")
        set(NEURAL_OP_ENHANCE8PMAC4_ELF "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac4.elf")
        set(NEURAL_OP_ENHANCE8PMAC4_BIN "${CMAKE_CURRENT_BINARY_DIR}/neural-op-enhance8pmac4.bin")
        set(NEURAL_MODEL_JSON "${CMAKE_CURRENT_SOURCE_DIR}/../weight-export/character_generator.json")
        set(NEURAL_COMPILER "${CMAKE_CURRENT_SOURCE_DIR}/model_compiler_interactive.py")
        # model_compiler_interactive.py subclasses/imports model_compiler.py, so
        # asm generation must also depend on the core compiler to avoid stale outputs.
        set(NEURAL_COMPILER_CORE "${CMAKE_CURRENT_SOURCE_DIR}/model_compiler.py")
        set(MOVEMENT_EXPORT_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/export_intermediate.py")
        set(MOVEMENT_MODEL_CHECKPOINT "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/movement_model.pth")
        # Use pre-exported JSON if available, otherwise generate in build directory
        if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/movement_generator.json")
            set(MOVEMENT_JSON "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/movement_generator.json")
            message(STATUS "Using pre-exported movement model JSON from source directory")
        else()
            set(MOVEMENT_JSON "${CMAKE_CURRENT_BINARY_DIR}/movement_generator.json")
            message(STATUS "Will generate movement model JSON in build directory")
        endif()
        set(MOVEMENT_ASM "${CMAKE_CURRENT_BINARY_DIR}/movement.s")
        set(MOVEMENT_OBJ "${CMAKE_CURRENT_BINARY_DIR}/movement.o")
        set(MOVEMENT_ELF "${CMAKE_CURRENT_BINARY_DIR}/movement.elf")
            set(GAME_MOVEMENT_EXPORT_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/export_squash_intermediate.py")
            set(GAME_MOVEMENT_MODEL_CHECKPOINT "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/squash_model.pth")
            set(GAME_MOVEMENT_JSON "${CMAKE_CURRENT_BINARY_DIR}/game-movement_generator.json")
            set(GAME_MOVEMENT_ASM "${CMAKE_CURRENT_BINARY_DIR}/game-movement.s")
            set(GAME_MOVEMENT_OBJ "${CMAKE_CURRENT_BINARY_DIR}/game-movement.o")
            set(GAME_MOVEMENT_ELF "${CMAKE_CURRENT_BINARY_DIR}/game-movement.elf")
            set(COUNTER_CHAR_EXPORT_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/export_counter_char_scaffold.py")
            set(COUNTER_CHAR_BASE_JSON "${CMAKE_CURRENT_SOURCE_DIR}/../weight-export/character_generator.json")
            set(COUNTER_CHAR_JSON "${CMAKE_CURRENT_BINARY_DIR}/counter-char_generator.json")
            set(COUNTER_CHAR_ASM "${CMAKE_CURRENT_BINARY_DIR}/counter-char.s")
            set(COUNTER_CHAR_OBJ "${CMAKE_CURRENT_BINARY_DIR}/counter-char.o")
            set(COUNTER_CHAR_ELF "${CMAKE_CURRENT_BINARY_DIR}/counter-char.elf")
            set(COUNTER255_EXPORT_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/export_counter255_intermediate.py")
            set(COUNTER255_JSON "${CMAKE_CURRENT_BINARY_DIR}/counter255_generator.json")
            set(COUNTER255_ASM "${CMAKE_CURRENT_BINARY_DIR}/counter255.s")
            set(COUNTER255_OBJ "${CMAKE_CURRENT_BINARY_DIR}/counter255.o")
            set(COUNTER255_ELF "${CMAKE_CURRENT_BINARY_DIR}/counter255.elf")
            set(COUNTER_CHAR_COMPOSE_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/export_counter_char_combined.py")
            set(COUNTER_CHAR_COMBINED_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_counter_char_combined.py")
            set(COUNTER_CHAR_COMBINED_JSON "${CMAKE_CURRENT_BINARY_DIR}/counter-char-combined_generator.json")
            set(COUNTER_CHAR_COMBINED_ASM "${CMAKE_CURRENT_BINARY_DIR}/counter-char-combined.s")
            set(COUNTER_CHAR_COMBINED_OBJ "${CMAKE_CURRENT_BINARY_DIR}/counter-char-combined.o")
            set(COUNTER_CHAR_COMBINED_ELF "${CMAKE_CURRENT_BINARY_DIR}/counter-char-combined.elf")
            set(COUNTER_CHAR_STATIC_OFFSET_EXPORT_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/export_counter_char_static.py")
            set(COUNTER_CHAR_STATIC_CHARGEN_BASE_JSON "${CMAKE_CURRENT_SOURCE_DIR}/../weight-export/character_generator.json")
            set(COUNTER_CHAR_STATIC_COMPOSE_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/export_counter_char_static_compose.py")
            set(COUNTER_CHAR_STATIC_OFFSET_JSON_TEMP "${CMAKE_CURRENT_BINARY_DIR}/counter_char_static_offset_temp.json")
            set(COUNTER_CHAR_STATIC_CHARGEN_JSON_TEMP "${CMAKE_CURRENT_BINARY_DIR}/counter_char_static_chargen_temp.json")
            set(COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/counter-char-static_generator.json")
            set(COUNTER_CHAR_STATIC_COMBINED_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_counter_char_static.py")
            set(COUNTER_CHAR_STATIC_ASM "${CMAKE_CURRENT_BINARY_DIR}/counter-char-static.s")
            set(COUNTER_CHAR_STATIC_OBJ "${CMAKE_CURRENT_BINARY_DIR}/counter-char-static.o")
            set(COUNTER_CHAR_STATIC_ELF "${CMAKE_CURRENT_BINARY_DIR}/counter-char-static.elf")

        add_custom_command(
            OUTPUT ${NEURAL_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${NEURAL_ASM} ${NEURAL_MODEL_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
            COMMENT "Generating neural.s from model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${NEURAL_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${NEURAL_OBJ} ${NEURAL_ASM}
            DEPENDS ${NEURAL_ASM}
            COMMENT "Assembling neural.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${NEURAL_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_ELF} ${NEURAL_OBJ}
            DEPENDS ${NEURAL_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking neural.elf"
            VERBATIM
        )

        add_custom_target(neural_elf ALL DEPENDS ${NEURAL_ELF})

        # Custom command to ensure movement model exists and export JSON
        set(MOVEMENT_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_movement_model.py")
        add_custom_command(
            OUTPUT ${MOVEMENT_JSON}
            COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src
            COMMAND ${CMAKE_COMMAND} -E env 
                MOVEMENT_MODEL_CHECKPOINT=${MOVEMENT_MODEL_CHECKPOINT} 
                MOVEMENT_TRAIN_SCRIPT=${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/train.py 
                MOVEMENT_EXPORT_SCRIPT=${MOVEMENT_EXPORT_SCRIPT} 
                MOVEMENT_JSON_OUTPUT=${MOVEMENT_JSON} 
                ${PYTHON_EXECUTABLE} ${MOVEMENT_BUILD_SCRIPT}
            DEPENDS ${MOVEMENT_BUILD_SCRIPT} ${MOVEMENT_EXPORT_SCRIPT}
            COMMENT "Building movement model (training if needed and exporting JSON)"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${MOVEMENT_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${MOVEMENT_ASM} ${MOVEMENT_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${MOVEMENT_JSON}
            COMMENT "Generating movement.s from movement model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${MOVEMENT_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${MOVEMENT_OBJ} ${MOVEMENT_ASM}
            DEPENDS ${MOVEMENT_ASM}
            COMMENT "Assembling movement.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${MOVEMENT_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${MOVEMENT_ELF} ${MOVEMENT_OBJ}
            DEPENDS ${MOVEMENT_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking movement.elf"
            VERBATIM
        )

        add_custom_target(movement_elf ALL DEPENDS ${MOVEMENT_ELF})

        # Build game-movement.elf from squash model (j/k input + 20x20 framebuffer output)
        set(GAME_MOVEMENT_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_game_movement_model.py")
        add_custom_command(
            OUTPUT ${GAME_MOVEMENT_JSON}
            COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src
            COMMAND ${CMAKE_COMMAND} -E env
                GAME_MOVEMENT_MODEL_CHECKPOINT=${GAME_MOVEMENT_MODEL_CHECKPOINT}
                GAME_MOVEMENT_TRAIN_SCRIPT=${CMAKE_CURRENT_SOURCE_DIR}/../game-movement/src/train_squash.py
                GAME_MOVEMENT_EXPORT_SCRIPT=${GAME_MOVEMENT_EXPORT_SCRIPT}
                GAME_MOVEMENT_JSON_OUTPUT=${GAME_MOVEMENT_JSON}
                ${PYTHON_EXECUTABLE} ${GAME_MOVEMENT_BUILD_SCRIPT}
            DEPENDS ${GAME_MOVEMENT_BUILD_SCRIPT} ${GAME_MOVEMENT_EXPORT_SCRIPT}
            COMMENT "Building game movement model (train if needed, then export JSON)"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${GAME_MOVEMENT_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${GAME_MOVEMENT_ASM} ${GAME_MOVEMENT_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${GAME_MOVEMENT_JSON}
            COMMENT "Generating game-movement.s from squash model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${GAME_MOVEMENT_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${GAME_MOVEMENT_OBJ} ${GAME_MOVEMENT_ASM}
            DEPENDS ${GAME_MOVEMENT_ASM}
            COMMENT "Assembling game-movement.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${GAME_MOVEMENT_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${GAME_MOVEMENT_ELF} ${GAME_MOVEMENT_OBJ}
            DEPENDS ${GAME_MOVEMENT_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking game-movement.elf"
            VERBATIM
        )

        add_custom_target(game_movement_elf DEPENDS ${GAME_MOVEMENT_ELF})

        # Phase-1 scaffold path for counter->a0->char-gen integration
        set(COUNTER_CHAR_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_counter_char_model.py")
        add_custom_command(
            OUTPUT ${COUNTER_CHAR_JSON}
            COMMAND ${CMAKE_COMMAND} -E env
                COUNTER_CHAR_BASE_JSON=${COUNTER_CHAR_BASE_JSON}
                COUNTER_CHAR_EXPORT_SCRIPT=${COUNTER_CHAR_EXPORT_SCRIPT}
                COUNTER_CHAR_JSON_OUTPUT=${COUNTER_CHAR_JSON}
                ${PYTHON_EXECUTABLE} ${COUNTER_CHAR_BUILD_SCRIPT}
            DEPENDS ${COUNTER_CHAR_BUILD_SCRIPT} ${COUNTER_CHAR_EXPORT_SCRIPT} ${COUNTER_CHAR_BASE_JSON}
            COMMENT "Building counter-char scaffold JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${COUNTER_CHAR_ASM} ${COUNTER_CHAR_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${COUNTER_CHAR_JSON}
            COMMENT "Generating counter-char.s from scaffold JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${COUNTER_CHAR_OBJ} ${COUNTER_CHAR_ASM}
            DEPENDS ${COUNTER_CHAR_ASM}
            COMMENT "Assembling counter-char.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${COUNTER_CHAR_ELF} ${COUNTER_CHAR_OBJ}
            DEPENDS ${COUNTER_CHAR_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking counter-char.elf"
            VERBATIM
        )

        add_custom_target(counter_char_elf DEPENDS ${COUNTER_CHAR_ELF})

        # Standalone counter255 runtime path (phase 3)
        set(COUNTER255_BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build_counter255_model.py")
        add_custom_command(
            OUTPUT ${COUNTER255_JSON}
            COMMAND ${CMAKE_COMMAND} -E env
                COUNTER255_EXPORT_SCRIPT=${COUNTER255_EXPORT_SCRIPT}
                COUNTER255_JSON_OUTPUT=${COUNTER255_JSON}
                ${PYTHON_EXECUTABLE} ${COUNTER255_BUILD_SCRIPT}
            DEPENDS ${COUNTER255_BUILD_SCRIPT} ${COUNTER255_EXPORT_SCRIPT}
            COMMENT "Building counter255 model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER255_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${COUNTER255_ASM} ${COUNTER255_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${COUNTER255_JSON}
            COMMENT "Generating counter255.s from counter255 model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER255_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${COUNTER255_OBJ} ${COUNTER255_ASM}
            DEPENDS ${COUNTER255_ASM}
            COMMENT "Assembling counter255.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER255_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${COUNTER255_ELF} ${COUNTER255_OBJ}
            DEPENDS ${COUNTER255_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking counter255.elf"
            VERBATIM
        )

        add_custom_target(counter255_elf DEPENDS ${COUNTER255_ELF})

        # Phase 5: Combined counter-chargen model
        add_custom_command(
            OUTPUT ${COUNTER_CHAR_COMBINED_JSON}
            COMMAND ${CMAKE_COMMAND} -E env
                COUNTER_CHAR_COUNTER_EXPORT_SCRIPT=${COUNTER255_EXPORT_SCRIPT}
                COUNTER_CHAR_CHARGEN_BASE_JSON=${COUNTER_CHAR_BASE_JSON}
                COUNTER_CHAR_COMPOSE_SCRIPT=${COUNTER_CHAR_COMPOSE_SCRIPT}
                COUNTER_CHAR_COUNTER_JSON_TEMP=${CMAKE_CURRENT_BINARY_DIR}/counter255_temp.json
                COUNTER_CHAR_CHARGEN_JSON_TEMP=${CMAKE_CURRENT_BINARY_DIR}/chargen_temp.json
                COUNTER_CHAR_COMBINED_JSON_OUTPUT=${COUNTER_CHAR_COMBINED_JSON}
                ${PYTHON_EXECUTABLE} ${COUNTER_CHAR_COMBINED_BUILD_SCRIPT}
            DEPENDS ${COUNTER_CHAR_COMBINED_BUILD_SCRIPT} ${COUNTER_CHAR_COMPOSE_SCRIPT} ${COUNTER255_EXPORT_SCRIPT} ${COUNTER_CHAR_BASE_JSON}
            COMMENT "Building combined counter-chargen model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_COMBINED_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${COUNTER_CHAR_COMBINED_ASM} ${COUNTER_CHAR_COMBINED_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${COUNTER_CHAR_COMBINED_JSON}
            COMMENT "Generating counter-char-combined.s from combined JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_COMBINED_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${COUNTER_CHAR_COMBINED_OBJ} ${COUNTER_CHAR_COMBINED_ASM}
            DEPENDS ${COUNTER_CHAR_COMBINED_ASM}
            COMMENT "Assembling counter-char-combined.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_COMBINED_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${COUNTER_CHAR_COMBINED_ELF} ${COUNTER_CHAR_COMBINED_OBJ}
            DEPENDS ${COUNTER_CHAR_COMBINED_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking counter-char-combined.elf"
            VERBATIM
        )

        add_custom_target(counter_char_combined_elf DEPENDS ${COUNTER_CHAR_COMBINED_ELF})

        # Phase 5b: Static counter-chargen model (non-incrementing version for testing)
        add_custom_command(
            OUTPUT ${COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT}
            COMMAND ${CMAKE_COMMAND} -E env
                COUNTER_CHAR_STATIC_OFFSET_EXPORT_SCRIPT=${COUNTER_CHAR_STATIC_OFFSET_EXPORT_SCRIPT}
                COUNTER_CHAR_STATIC_CHARGEN_BASE_JSON=${COUNTER_CHAR_STATIC_CHARGEN_BASE_JSON}
                COUNTER_CHAR_STATIC_COMPOSE_SCRIPT=${COUNTER_CHAR_STATIC_COMPOSE_SCRIPT}
                COUNTER_CHAR_STATIC_OFFSET_JSON_TEMP=${COUNTER_CHAR_STATIC_OFFSET_JSON_TEMP}
                COUNTER_CHAR_STATIC_CHARGEN_JSON_TEMP=${COUNTER_CHAR_STATIC_CHARGEN_JSON_TEMP}
                COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT=${COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT}
                ${PYTHON_EXECUTABLE} ${COUNTER_CHAR_STATIC_COMBINED_BUILD_SCRIPT}
            DEPENDS ${COUNTER_CHAR_STATIC_COMBINED_BUILD_SCRIPT} ${COUNTER_CHAR_STATIC_COMPOSE_SCRIPT} ${COUNTER_CHAR_STATIC_OFFSET_EXPORT_SCRIPT} ${COUNTER_CHAR_STATIC_CHARGEN_BASE_JSON}
            COMMENT "Building static counter-chargen model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_STATIC_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${COUNTER_CHAR_STATIC_ASM} ${COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT}
            COMMENT "Generating counter-char-static.s from static model JSON"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_STATIC_OBJ}
            COMMAND ${RISCV_AS} -march=rv32if -mabi=ilp32f -o ${COUNTER_CHAR_STATIC_OBJ} ${COUNTER_CHAR_STATIC_ASM}
            DEPENDS ${COUNTER_CHAR_STATIC_ASM}
            COMMENT "Assembling counter-char-static.o"
            VERBATIM
        )

        add_custom_command(
            OUTPUT ${COUNTER_CHAR_STATIC_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${COUNTER_CHAR_STATIC_ELF} ${COUNTER_CHAR_STATIC_OBJ}
            DEPENDS ${COUNTER_CHAR_STATIC_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            COMMENT "Linking counter-char-static.elf"
            VERBATIM
        )

        add_custom_target(counter_char_static_elf DEPENDS ${COUNTER_CHAR_STATIC_ELF})

        if(RV32AS_EXECUTABLE)
            add_custom_command(
                OUTPUT ${NEURAL_OPSX77_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops -o ${NEURAL_OPSX77_ASM} -b ${NEURAL_OPSX77_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-ai-opsx77.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OPSX77_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OPSX77_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OPSX77_OBJ}
                DEPENDS ${NEURAL_OPSX77_ASM} rv32as_build
                COMMENT "Assembling neural-ai-opsx77.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OPSX77_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OPSX77_ELF} ${NEURAL_OPSX77_OBJ}
                DEPENDS ${NEURAL_OPSX77_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-ai-opsx77.elf"
                VERBATIM
            )

            add_custom_target(neural_opsx77_elf ALL DEPENDS ${NEURAL_OPSX77_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b -o ${NEURAL_OP_ENHANCE_ASM} -b ${NEURAL_OP_ENHANCE_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE_ELF} ${NEURAL_OP_ENHANCE_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance_elf ALL DEPENDS ${NEURAL_OP_ENHANCE_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE4_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 4x -o ${NEURAL_OP_ENHANCE4_ASM} -b ${NEURAL_OP_ENHANCE4_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance4.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE4_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE4_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE4_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE4_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance4.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE4_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE4_ELF} ${NEURAL_OP_ENHANCE4_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE4_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance4.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance4_elf ALL DEPENDS ${NEURAL_OP_ENHANCE4_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 8x -o ${NEURAL_OP_ENHANCE8_ASM} -b ${NEURAL_OP_ENHANCE8_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance8.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE8_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE8_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance8.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE8_ELF} ${NEURAL_OP_ENHANCE8_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance8.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance8_elf ALL DEPENDS ${NEURAL_OP_ENHANCE8_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 8xpmac -o ${NEURAL_OP_ENHANCE8PMAC_ASM} -b ${NEURAL_OP_ENHANCE8PMAC_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance8pmac.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE8PMAC_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE8PMAC_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance8pmac.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE8PMAC_ELF} ${NEURAL_OP_ENHANCE8PMAC_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance8pmac.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance8pmac_elf ALL DEPENDS ${NEURAL_OP_ENHANCE8PMAC_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC2_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 8xpmac2 -o ${NEURAL_OP_ENHANCE8PMAC2_ASM} -b ${NEURAL_OP_ENHANCE8PMAC2_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance8pmac2.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC2_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE8PMAC2_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE8PMAC2_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC2_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance8pmac2.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC2_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE8PMAC2_ELF} ${NEURAL_OP_ENHANCE8PMAC2_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC2_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance8pmac2.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance8pmac2_elf ALL DEPENDS ${NEURAL_OP_ENHANCE8PMAC2_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC3_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 8xpmac3 -o ${NEURAL_OP_ENHANCE8PMAC3_ASM} -b ${NEURAL_OP_ENHANCE8PMAC3_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance8pmac3.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC3_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE8PMAC3_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE8PMAC3_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC3_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance8pmac3.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC3_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE8PMAC3_ELF} ${NEURAL_OP_ENHANCE8PMAC3_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC3_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance8pmac3.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance8pmac3_elf ALL DEPENDS ${NEURAL_OP_ENHANCE8PMAC3_ELF})

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC4_ASM}
                COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} --use-neural-ops --neural-opcode x7b --neural-lane-mode 8xpmac4 -o ${NEURAL_OP_ENHANCE8PMAC4_ASM} -b ${NEURAL_OP_ENHANCE8PMAC4_BIN} ${NEURAL_MODEL_JSON}
                DEPENDS ${NEURAL_COMPILER} ${NEURAL_COMPILER_CORE} ${NEURAL_MODEL_JSON}
                COMMENT "Generating neural-op-enhance8pmac4.s from model JSON"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC4_OBJ}
                COMMAND ${RV32AS_EXECUTABLE} ${NEURAL_OP_ENHANCE8PMAC4_ASM} -march rv32if -mabi ilp32f -o ${NEURAL_OP_ENHANCE8PMAC4_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC4_ASM} rv32as_build
                COMMENT "Assembling neural-op-enhance8pmac4.o with rv32as"
                VERBATIM
            )

            add_custom_command(
                OUTPUT ${NEURAL_OP_ENHANCE8PMAC4_ELF}
                COMMAND ${RISCV_LD} -m elf32lriscv -T ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld -o ${NEURAL_OP_ENHANCE8PMAC4_ELF} ${NEURAL_OP_ENHANCE8PMAC4_OBJ}
                DEPENDS ${NEURAL_OP_ENHANCE8PMAC4_OBJ} ${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
                COMMENT "Linking neural-op-enhance8pmac4.elf"
                VERBATIM
            )

            add_custom_target(neural_op_enhance8pmac4_elf ALL DEPENDS ${NEURAL_OP_ENHANCE8PMAC4_ELF})
        else()
            message(WARNING "rv32as not found - neural_opsx77_elf and neural_op_enhance* targets disabled")
        endif()
    else()
        message(WARNING "Python not found - neural_elf target disabled")
    endif()

    # Create target to build all blackbox test artifacts
    add_blackbox_all_target()
endif()

# Neural Character Generation Validation Test (requires Python + rv32as)
if(PYTHON_EXECUTABLE AND RV32AS_EXECUTABLE)
    add_test(
        NAME python/neural_char_gen/validation_256_base
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_neural_256_chars.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    set_tests_properties(python/neural_char_gen/validation_256_base PROPERTIES
        LABELS "neural;validation;blackbox"
        TIMEOUT 600
        ENVIRONMENT "EMULATOR_NEW_ASSEMBLER=${RV32AS_EXECUTABLE};EMULATOR_BACKEND=cpp;NEURAL_LANE_MODE=base"
    )
    add_test(
        NAME python/neural_char_gen/validation_256_4x
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_neural_256_chars.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    set_tests_properties(python/neural_char_gen/validation_256_4x PROPERTIES
        LABELS "neural;validation;blackbox"
        TIMEOUT 600
        ENVIRONMENT "EMULATOR_NEW_ASSEMBLER=${RV32AS_EXECUTABLE};EMULATOR_BACKEND=cpp;NEURAL_LANE_MODE=4x"
    )
    add_test(
        NAME python/neural_char_gen/validation_256_8x
        COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_neural_256_chars.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    set_tests_properties(python/neural_char_gen/validation_256_8x PROPERTIES
        LABELS "neural;validation;blackbox"
        TIMEOUT 600
        ENVIRONMENT "EMULATOR_NEW_ASSEMBLER=${RV32AS_EXECUTABLE};EMULATOR_BACKEND=cpp;NEURAL_LANE_MODE=8x"
    )
elseif(NOT RV32AS_EXECUTABLE)
    message(WARNING "rv32as not available - python/neural_char_gen/validation_256_* tests disabled")
endif()

# Ensure rv32as binary exists before tests that depend on it.
if(RV32AS_EXECUTABLE)
    add_test(
        NAME python/fixture/build_rv32as
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target rv32as_build
    )
    set_tests_properties(python/fixture/build_rv32as PROPERTIES
        LABELS "assembler;fixture"
        FIXTURES_SETUP rv32as_ready
    )

    if(TEST python/assembler/neural_instr_encoding)
        set_tests_properties(python/assembler/neural_instr_encoding PROPERTIES
            FIXTURES_REQUIRED rv32as_ready
        )
    endif()
    if(TEST python/neural_char_gen/validation_256_base)
        set_tests_properties(python/neural_char_gen/validation_256_base PROPERTIES
            FIXTURES_REQUIRED rv32as_ready
        )
    endif()
    if(TEST python/neural_char_gen/validation_256_4x)
        set_tests_properties(python/neural_char_gen/validation_256_4x PROPERTIES
            FIXTURES_REQUIRED rv32as_ready
        )
    endif()
    if(TEST python/neural_char_gen/validation_256_8x)
        set_tests_properties(python/neural_char_gen/validation_256_8x PROPERTIES
            FIXTURES_REQUIRED rv32as_ready
        )
    endif()
endif()

add_test(
    NAME python/verilator/differential_validation
    COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_verilator_differential.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(python/verilator/differential_validation PROPERTIES
    LABELS "verilator;differential;validation"
    TIMEOUT 720
)

add_test(
    NAME python/verilator/neural_opsx77
    COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_verilator_neural_opsx77.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(python/verilator/neural_opsx77 PROPERTIES
    LABELS "verilator;neural;opsx77;validation"
    TIMEOUT 180
)

add_test(
    NAME python/verilator/neural_op_enhance
    COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_verilator_neural_op_enhance.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(python/verilator/neural_op_enhance PROPERTIES
    LABELS "verilator;neural;enhance;validation"
    TIMEOUT 180
    ENVIRONMENT "NEURAL_ENHANCE_VARIANTS=base,4x,8x,8xpmac,8xpmac2,8xpmac3,8xpmac4"
)

# ============================================================================
# Phase D.1: Parity Testing (Rust assembler vs GNU assembler)
# ============================================================================

include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/PurityTesting.cmake)

if(GNU_ASM_AVAILABLE AND RV32AS_EXECUTABLE)
    message(STATUS "Setting up parity tests for Phase D.1...")

    # Explicitly build rv32as before any parity test runs.
    add_test(
        NAME parity/fixture/build_rv32as
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target rv32as_build
    )
    set_tests_properties(parity/fixture/build_rv32as PROPERTIES
        LABELS "parity;phase_d1"
        FIXTURES_SETUP rv32as_built
    )
    
    # Add parity tests for all assembly directories
    file(GLOB_RECURSE ASM_TEST_FILES "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/asm/*/test.s")
    
    foreach(ASM_FILE ${ASM_TEST_FILES})
        get_filename_component(ASM_DIR ${ASM_FILE} DIRECTORY)
        get_filename_component(DIR_NAME ${ASM_DIR} NAME)
        get_filename_component(PARENT_DIR ${ASM_DIR} DIRECTORY)
        get_filename_component(PARENT_NAME ${PARENT_DIR} NAME)
        
        set(TEST_NAME "parity/${PARENT_NAME}/${DIR_NAME}")
        add_parity_test(${TEST_NAME} ${ASM_FILE})
    endforeach()
    
    list(LENGTH ASM_TEST_FILES NUM_PARITY_TESTS)
    message(STATUS "  ${NUM_PARITY_TESTS} parity tests configured")

    # Add parity tests for C corpus via GCC -> assembly -> (rv32as vs GNU as)
    if(RISCV_GCC AND PYTHON_EXECUTABLE)
        file(GLOB_RECURSE C_PARITY_FILES "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/c/**/test.c")
        foreach(C_FILE ${C_PARITY_FILES})
            get_filename_component(C_DIR ${C_FILE} DIRECTORY)
            get_filename_component(DIR_NAME ${C_DIR} NAME)
            get_filename_component(PARENT_DIR ${C_DIR} DIRECTORY)
            get_filename_component(PARENT_NAME ${PARENT_DIR} NAME)

            # Defaults
            set(C_MARCH "rv32i")
            set(C_MABI "ilp32")

            set(C_CONFIG "${C_DIR}/config.txt")
            if(EXISTS ${C_CONFIG})
                file(STRINGS ${C_CONFIG} CONFIG_LINES)
                foreach(LINE ${CONFIG_LINES})
                    if(LINE MATCHES "^march=(.*)$")
                        set(C_MARCH "${CMAKE_MATCH_1}")
                    elseif(LINE MATCHES "^mabi=(.*)$")
                        set(C_MABI "${CMAKE_MATCH_1}")
                    endif()
                endforeach()
            endif()

            # Keep baseline ABI heuristic for F-extension tests.
            if(C_MABI STREQUAL "ilp32" AND C_MARCH MATCHES ".*f.*")
                set(C_MABI "ilp32f")
            endif()

            set(C_PARITY_TEST_NAME "parity/c/${PARENT_NAME}/${DIR_NAME}")
            add_c_parity_test(${C_PARITY_TEST_NAME} ${C_FILE} ${C_MARCH} ${C_MABI})
        endforeach()
        list(LENGTH C_PARITY_FILES NUM_C_PARITY_TESTS)
        message(STATUS "  ${NUM_C_PARITY_TESTS} C parity tests configured")
    else()
        message(WARNING "C parity tests disabled (missing RISCV_GCC or Python)")
    endif()
else()
    message(WARNING "Parity tests disabled (GNU assembler or Rust assembler not available)")
endif()


# ============================================================================
# HDL (Verilog) Simulation with Verilator
# ============================================================================
add_subdirectory(hdl)
