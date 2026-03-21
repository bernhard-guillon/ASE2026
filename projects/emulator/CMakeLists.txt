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
