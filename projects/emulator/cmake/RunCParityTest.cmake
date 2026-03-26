# C parity test runner:
# 1) compile C to assembly with GCC
# 2) normalize GCC assembly to syntax subset supported by rv32as
# 3) assemble normalized assembly with rv32as and GNU as
# 4) compare extracted .text bytes

if(NOT DEFINED RUST_ASSEMBLER OR NOT DEFINED GNU_ASSEMBLER OR NOT DEFINED GNU_GCC OR
   NOT DEFINED INPUT_C OR NOT DEFINED GCC_ASM OR NOT DEFINED NORMALIZED_ASM OR
   NOT DEFINED PREPROCESS_SCRIPT OR NOT DEFINED PYTHON_EXECUTABLE)
    message(FATAL_ERROR "Missing required parameters")
endif()

if(NOT DEFINED MARCH)
    set(MARCH rv32i)
endif()

if(NOT DEFINED MABI)
    set(MABI ilp32)
endif()

execute_process(
    COMMAND ${GNU_GCC}
        -march=${MARCH}
        -mabi=${MABI}
        -S
        -O0
        -fno-asynchronous-unwind-tables
        -fno-stack-protector
        -fno-ident
        -mno-relax
        -mno-save-restore
        -mno-explicit-relocs
        ${INPUT_C}
        -o ${GCC_ASM}
    RESULT_VARIABLE GCC_RESULT
    OUTPUT_VARIABLE GCC_STDOUT
    ERROR_VARIABLE GCC_STDERR
)

if(NOT GCC_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ GCC -S failed for ${TEST_NAME}:\n${GCC_STDERR}")
endif()

execute_process(
    COMMAND ${PYTHON_EXECUTABLE} ${PREPROCESS_SCRIPT} ${GCC_ASM} ${NORMALIZED_ASM}
    RESULT_VARIABLE PREPROC_RESULT
    OUTPUT_VARIABLE PREPROC_STDOUT
    ERROR_VARIABLE PREPROC_STDERR
)

if(NOT PREPROC_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ preprocess failed for ${TEST_NAME}:\n${PREPROC_STDERR}")
endif()

execute_process(
    COMMAND ${RUST_ASSEMBLER} ${NORMALIZED_ASM} -o ${RUST_OUTPUT}
    RESULT_VARIABLE RUST_RESULT
    OUTPUT_VARIABLE RUST_STDOUT
    ERROR_VARIABLE RUST_STDERR
)

if(NOT RUST_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ Rust assembler failed for ${TEST_NAME}:\n${RUST_STDERR}")
endif()

execute_process(
    COMMAND ${GNU_ASSEMBLER} -march=${MARCH} -mabi=${MABI} ${NORMALIZED_ASM} -o ${GNU_OBJECT}
    RESULT_VARIABLE GNU_RESULT
    OUTPUT_VARIABLE GNU_STDOUT
    ERROR_VARIABLE GNU_STDERR
)

if(NOT GNU_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ GNU assembler failed for ${TEST_NAME}:\n${GNU_STDERR}")
endif()

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

if(DEFINED C_PARITY_COMPARE_LINKED AND C_PARITY_COMPARE_LINKED AND DEFINED LINKER AND EXISTS "${LINKER}")
    set(RUST_LINKED_ELF "${RUST_OUTPUT}.linked.elf")
    set(GNU_LINKED_ELF "${GNU_OBJECT}.linked.elf")
    set(RUST_LINKED_TEXT "${RUST_OUTPUT}.linked.text.bin")
    set(GNU_LINKED_TEXT "${GNU_OBJECT}.linked.text.bin")

    execute_process(
        COMMAND ${LINKER} -m elf32lriscv -T ${LINKER_SCRIPT} -o ${RUST_LINKED_ELF} ${RUST_OUTPUT}
        RESULT_VARIABLE RUST_LINK_RESULT
        OUTPUT_VARIABLE RUST_LINK_STDOUT
        ERROR_VARIABLE RUST_LINK_STDERR
    )
    if(NOT RUST_LINK_RESULT EQUAL 0)
        message(FATAL_ERROR "✗ link failed on Rust object for ${TEST_NAME}:\n${RUST_LINK_STDERR}")
    endif()

    execute_process(
        COMMAND ${LINKER} -m elf32lriscv -T ${LINKER_SCRIPT} -o ${GNU_LINKED_ELF} ${GNU_OBJECT}
        RESULT_VARIABLE GNU_LINK_RESULT
        OUTPUT_VARIABLE GNU_LINK_STDOUT
        ERROR_VARIABLE GNU_LINK_STDERR
    )
    if(NOT GNU_LINK_RESULT EQUAL 0)
        message(FATAL_ERROR "✗ link failed on GNU object for ${TEST_NAME}:\n${GNU_LINK_STDERR}")
    endif()

    execute_process(
        COMMAND ${OBJ_COPY} -O binary -j .text ${RUST_LINKED_ELF} ${RUST_LINKED_TEXT}
        RESULT_VARIABLE RUST_LINK_OBJCOPY_RESULT
        OUTPUT_VARIABLE RUST_LINK_OBJCOPY_STDOUT
        ERROR_VARIABLE RUST_LINK_OBJCOPY_STDERR
    )
    if(NOT RUST_LINK_OBJCOPY_RESULT EQUAL 0)
        message(FATAL_ERROR "✗ objcopy linked Rust .text failed for ${TEST_NAME}:\n${RUST_LINK_OBJCOPY_STDERR}")
    endif()

    execute_process(
        COMMAND ${OBJ_COPY} -O binary -j .text ${GNU_LINKED_ELF} ${GNU_LINKED_TEXT}
        RESULT_VARIABLE GNU_LINK_OBJCOPY_RESULT
        OUTPUT_VARIABLE GNU_LINK_OBJCOPY_STDOUT
        ERROR_VARIABLE GNU_LINK_OBJCOPY_STDERR
    )
    if(NOT GNU_LINK_OBJCOPY_RESULT EQUAL 0)
        message(FATAL_ERROR "✗ objcopy linked GNU .text failed for ${TEST_NAME}:\n${GNU_LINK_OBJCOPY_STDERR}")
    endif()

    file(SIZE "${RUST_LINKED_TEXT}" RUST_LINKED_SIZE)
    file(SIZE "${GNU_LINKED_TEXT}" GNU_LINKED_SIZE)
    if(NOT RUST_LINKED_SIZE EQUAL GNU_LINKED_SIZE)
        message(FATAL_ERROR "✗ C PARITY MISMATCH: ${TEST_NAME} - linked size difference\n  Rust: ${RUST_LINKED_SIZE} bytes\n  GNU: ${GNU_LINKED_SIZE} bytes")
    endif()

    file(READ "${RUST_LINKED_TEXT}" RUST_LINKED_CONTENT HEX)
    file(READ "${GNU_LINKED_TEXT}" GNU_LINKED_CONTENT HEX)
    if(NOT RUST_LINKED_CONTENT STREQUAL GNU_LINKED_CONTENT)
        message(FATAL_ERROR "✗ C PARITY MISMATCH: ${TEST_NAME} - linked binary content differs")
    endif()

    message(STATUS "✓ C PARITY (linked): ${TEST_NAME} - ${RUST_LINKED_SIZE} bytes match")
    return()
endif()

execute_process(
    COMMAND ${OBJ_COPY} -O binary -j .text ${GNU_OBJECT} ${GNU_OUTPUT}
    RESULT_VARIABLE OBJCOPY_RESULT
    OUTPUT_VARIABLE OBJCOPY_STDOUT
    ERROR_VARIABLE OBJCOPY_STDERR
)

if(NOT OBJCOPY_RESULT EQUAL 0)
    message(FATAL_ERROR "✗ objcopy failed for ${TEST_NAME}:\n${OBJCOPY_STDERR}")
endif()

file(SIZE "${RUST_TEXT_OUTPUT}" RUST_SIZE)
file(SIZE "${GNU_OUTPUT}" GNU_SIZE)

if(NOT RUST_SIZE EQUAL GNU_SIZE)
    message(FATAL_ERROR "✗ C PARITY MISMATCH: ${TEST_NAME} - size difference\n  Rust: ${RUST_SIZE} bytes\n  GNU: ${GNU_SIZE} bytes")
endif()

file(READ "${RUST_TEXT_OUTPUT}" RUST_CONTENT HEX)
file(READ "${GNU_OUTPUT}" GNU_CONTENT HEX)

if(NOT RUST_CONTENT STREQUAL GNU_CONTENT)
    message(FATAL_ERROR "✗ C PARITY MISMATCH: ${TEST_NAME} - binary content differs")
endif()

message(STATUS "✓ C PARITY: ${TEST_NAME} - ${RUST_SIZE} bytes match")
