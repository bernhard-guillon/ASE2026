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
target_link_libraries(cpu memory instruction)

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
        set(NEURAL_MODEL_JSON "${CMAKE_CURRENT_SOURCE_DIR}/../weight-export/character_generator.json")
        set(NEURAL_COMPILER "${CMAKE_CURRENT_SOURCE_DIR}/model_compiler_interactive.py")

        add_custom_command(
            OUTPUT ${NEURAL_ASM}
            COMMAND ${PYTHON_EXECUTABLE} ${NEURAL_COMPILER} -o ${NEURAL_ASM} ${NEURAL_MODEL_JSON}
            DEPENDS ${NEURAL_COMPILER} ${NEURAL_MODEL_JSON}
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
    else()
        message(WARNING "Python not found - neural_elf target disabled")
    endif()

    # Create target to build all blackbox test artifacts
    add_blackbox_all_target()
endif()

# Neural Character Generation Validation Test
add_test(
    NAME python/neural_char_gen/validation_256
    COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_neural_256_chars.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(python/neural_char_gen/validation_256 PROPERTIES
    LABELS "neural;validation;blackbox"
    TIMEOUT 300
)

add_test(
    NAME python/verilator/differential_validation
    COMMAND ${PYTHON_EXECUTABLE} blackbox_tests/test_verilator_differential.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(python/verilator/differential_validation PROPERTIES
    LABELS "verilator;differential;validation"
    TIMEOUT 120
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
