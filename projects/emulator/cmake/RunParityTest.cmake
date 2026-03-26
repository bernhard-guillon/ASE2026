# Parity test runner: assembles with both tools and compares output
# This script is invoked by add_test() during test execution

if(NOT DEFINED RUST_ASSEMBLER OR NOT DEFINED GNU_ASSEMBLER OR NOT DEFINED INPUT_ASM)
    message(FATAL_ERROR "Missing required parameters")
endif()

# Assemble with Rust assembler (ELF object output)
execute_process(
    COMMAND ${RUST_ASSEMBLER} ${INPUT_ASM} -o ${RUST_OUTPUT}
    RESULT_VARIABLE RUST_RESULT
    OUTPUT_VARIABLE RUST_STDOUT
    ERROR_VARIABLE RUST_STDERR
)

if(NOT RUST_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ Rust assembler failed for ${TEST_NAME}:\n${RUST_STDERR}")
endif()

# Assemble with GNU assembler
execute_process(
    COMMAND ${GNU_ASSEMBLER} -march=rv32if -mabi=ilp32f ${INPUT_ASM} -o ${GNU_OBJECT}
    RESULT_VARIABLE GNU_RESULT
    OUTPUT_VARIABLE GNU_STDOUT
    ERROR_VARIABLE GNU_STDERR
)

if(NOT GNU_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ GNU assembler failed for ${TEST_NAME}:\n${GNU_STDERR}")
endif()

# Extract .text section from Rust object file
set(RUST_TEXT_OUTPUT "${RUST_OUTPUT}.text.bin")
execute_process(
    COMMAND ${OBJ_COPY} -O binary -j .text ${RUST_OUTPUT} ${RUST_TEXT_OUTPUT}
    RESULT_VARIABLE RUST_OBJCOPY_RESULT
    OUTPUT_VARIABLE RUST_OBJCOPY_STDOUT
    ERROR_VARIABLE RUST_OBJCOPY_STDERR
)

if(NOT RUST_OBJCOPY_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ objcopy failed on Rust output for ${TEST_NAME}:\n${RUST_OBJCOPY_STDERR}")
endif()

# Extract .text section from GNU object file
execute_process(
    COMMAND ${OBJ_COPY} -O binary -j .text ${GNU_OBJECT} ${GNU_OUTPUT}
    RESULT_VARIABLE OBJCOPY_RESULT
    OUTPUT_VARIABLE OBJCOPY_STDOUT
    ERROR_VARIABLE OBJCOPY_STDERR
)

if(NOT OBJCOPY_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ objcopy failed for ${TEST_NAME}:\n${OBJCOPY_STDERR}")
endif()

# Check if files exist
if(NOT EXISTS "${RUST_OUTPUT}")
    message(FATAL_ERROR "✗ Rust assembler did not produce output file: ${RUST_OUTPUT}")
endif()

if(NOT EXISTS "${GNU_OUTPUT}")
    message(FATAL_ERROR "✗ GNU assembler did not produce output file: ${GNU_OUTPUT}")
endif()

if(NOT EXISTS "${RUST_TEXT_OUTPUT}")
    message(FATAL_ERROR "✗ Rust .text extraction did not produce output file: ${RUST_TEXT_OUTPUT}")
endif()

# Get file sizes
file(SIZE "${RUST_TEXT_OUTPUT}" RUST_SIZE)
file(SIZE "${GNU_OUTPUT}" GNU_SIZE)

if(NOT RUST_SIZE EQUAL GNU_SIZE)
    message(FATAL_ERROR "✗ PARITY MISMATCH: ${TEST_NAME} - size difference\n  Rust: ${RUST_SIZE} bytes\n  GNU: ${GNU_SIZE} bytes")
endif()

# Read and compare binary contents
file(READ "${RUST_TEXT_OUTPUT}" RUST_CONTENT HEX)
file(READ "${GNU_OUTPUT}" GNU_CONTENT HEX)

if(NOT RUST_CONTENT STREQUAL GNU_CONTENT)
    message(FATAL_ERROR "✗ PARITY MISMATCH: ${TEST_NAME} - binary content differs")
endif()

# Success!
message(STATUS "✓ PARITY: ${TEST_NAME} - ${RUST_SIZE} bytes match")
