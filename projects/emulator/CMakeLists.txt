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

# Memory module
add_library(memory Memory.cpp)

# CPU module
add_library(cpu CPU.cpp)
target_link_libraries(cpu memory instruction)

# Instruction decoder module
add_library(instruction Instruction.cpp)

# Emulator module
add_library(emulator Emulator.cpp)
target_link_libraries(emulator cpu memory instruction)

# Memory tests
add_executable(test_memory test_memory.cpp)
target_link_libraries(test_memory memory gtest_main)

# CPU tests
add_executable(test_cpu test_cpu.cpp)
target_link_libraries(test_cpu cpu gtest_main)

# Instruction decoder tests
add_executable(test_instruction test_instruction.cpp)
target_link_libraries(test_instruction instruction gtest_main)

# Execution tests
add_executable(test_execution test_execution.cpp)
target_link_libraries(test_execution cpu memory instruction gtest_main)

# Emulator integration tests
add_executable(test_emulator test_emulator.cpp)
target_link_libraries(test_emulator emulator cpu memory instruction gtest_main)

# File I/O syscall tests
add_executable(test_file_io_syscalls test_file_io_syscalls.cpp)
target_link_libraries(test_file_io_syscalls emulator cpu memory instruction gtest_main)

# Memory syscall tests
add_executable(test_memory_syscalls test_memory_syscalls.cpp)
target_link_libraries(test_memory_syscalls emulator cpu memory instruction gtest_main)

# Instruction edge case tests
add_executable(test_instruction_edges test_instruction_edges.cpp)
target_link_libraries(test_instruction_edges cpu memory instruction gtest_main)

# Framebuffer tests
add_executable(test_framebuffer test_framebuffer.cpp)
target_link_libraries(test_framebuffer emulator cpu memory instruction gtest_main)

# ELF Loader tests
add_executable(test_elf_loader test_elf_loader.cpp)
target_link_libraries(test_elf_loader emulator cpu memory instruction gtest_main)

# Model loading tests
add_executable(test_model_loading test_model_loading.cpp)
target_link_libraries(test_model_loading emulator cpu memory instruction)

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
gtest_discover_tests(test_memory_syscalls)
gtest_discover_tests(test_instruction_edges)
gtest_discover_tests(test_framebuffer)
gtest_discover_tests(test_elf_loader)

# Register integration tests
add_test(NAME test_model_loading COMMAND test_model_loading)
add_test(NAME test_memory_layout COMMAND run_memory_layout_test)

# ============================================================================
# Blackbox Testing
# ============================================================================

# Find RISC-V toolchain
find_program(RISCV_GCC riscv64-elf-gcc)
find_program(RISCV_AS riscv64-elf-as)
find_program(RISCV_LD riscv64-elf-ld)
find_program(RISCV_OBJCOPY riscv64-elf-objcopy)

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
        message(WARNING "  Missing: riscv64-elf-gcc")
    endif()
    if(NOT RISCV_AS)
        message(WARNING "  Missing: riscv64-elf-as")
    endif()
    if(NOT RISCV_LD)
        message(WARNING "  Missing: riscv64-elf-ld")
    endif()
    if(NOT RISCV_OBJCOPY)
        message(WARNING "  Missing: riscv64-elf-objcopy")
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
        COMMAND ${PYTHON_EXECUTABLE} -m pytest test_model_compiler.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase1/model_compiler_blackbox
        COMMAND ${PYTHON_EXECUTABLE} -m pytest test_model_compiler_blackbox.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 2: Bootloader Code Generation Tests (no toolchain needed)
    add_test(
        NAME python/phase2/bootloader_unit
        COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase2.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/phase2/bootloader_blackbox
        COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase2_blackbox.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 3: Linker Script Configuration Tests (requires RISC-V toolchain)
    if(RISCV_TOOLCHAIN_FOUND)
        add_test(
            NAME python/phase3/linker_script_unit
            COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase3.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        add_test(
            NAME python/phase3/linker_script_blackbox
            COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase3_blackbox.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        add_test(
            NAME python/phase3/linker_script_integration
            COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase3_integration.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        # Phase 4: Full Pipeline Integration Tests (requires RISC-V toolchain)
        add_test(
            NAME python/phase4/pipeline_integration
            COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase4_integration.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        message(STATUS "Phase 3-4 Python tests registered (RISC-V toolchain available)")
    else()
        message(WARNING "RISC-V toolchain not found - Phase 3-4 Python tests skipped (require riscv64-elf-as, riscv64-elf-ld, riscv64-elf-objcopy)")
    endif()
    
    # Phase 5: CMake Build System Tests (no toolchain needed)
    add_test(
        NAME python/phase5/cmake_build_system
        COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase5.py -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Phase 6: Comprehensive Integration Tests (requires RISC-V toolchain)
    if(RISCV_TOOLCHAIN_FOUND)
        add_test(
            NAME python/phase6/comprehensive_integration
            COMMAND ${PYTHON_EXECUTABLE} -m pytest test_bootloader_phase6_integration.py -v
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        message(STATUS "Phase 6 Python tests registered (RISC-V toolchain available)")
    endif()
    
    # Static Character Generation Tests
    add_test(
        NAME python/static_char_gen/integration
        COMMAND ${PYTHON_EXECUTABLE} test_static_char_gen_integration.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    add_test(
        NAME python/static_char_gen/basic
        COMMAND ${PYTHON_EXECUTABLE} test_static_char_gen_basic.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # ELF Loader Tests
    add_test(
        NAME python/elf_loader/blackbox
        COMMAND ${PYTHON_EXECUTABLE} test_elf_loader_blackbox.py
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
    
    # Create target to build all blackbox test artifacts
    add_blackbox_all_target()
endif()
