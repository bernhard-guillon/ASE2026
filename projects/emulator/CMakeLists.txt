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

# Instruction decoder module
add_library(instruction Instruction.cpp)

# Memory tests
add_executable(test_memory test_memory.cpp)
target_link_libraries(test_memory memory gtest_main)

# CPU tests
add_executable(test_cpu test_cpu.cpp)
target_link_libraries(test_cpu cpu gtest_main)

# Instruction decoder tests
add_executable(test_instruction test_instruction.cpp)
target_link_libraries(test_instruction instruction gtest_main)

# Register tests with CTest
include(GoogleTest)
gtest_discover_tests(test_memory)
gtest_discover_tests(test_cpu)
gtest_discover_tests(test_instruction)
