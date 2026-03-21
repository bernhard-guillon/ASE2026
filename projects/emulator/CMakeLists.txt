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

if(RISCV_TOOLCHAIN_FOUND)
    # Include blackbox testing functions
    include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/BlackboxTests.cmake)
    
    # Discover and register all assembly tests
    add_blackbox_asm_tests()
    
    # Discover and register all C tests
    add_blackbox_c_tests()
    
    # Create target to build all blackbox test artifacts
    add_blackbox_all_target()
endif()
