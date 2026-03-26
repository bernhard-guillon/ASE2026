# Phase D.1: Parity testing infrastructure
# Compare Rust assembler output against GNU assembler

# Find the GNU assembler
find_program(RISCV_AS NAMES riscv64-elf-as riscv64-unknown-elf-as)
find_program(RISCV_OBJCOPY NAMES riscv64-elf-objcopy riscv64-unknown-elf-objcopy)

if(RISCV_AS AND RISCV_OBJCOPY)
    set(GNU_ASM_AVAILABLE TRUE)
    message(STATUS "GNU RISC-V assembler available for parity testing")
else()
    set(GNU_ASM_AVAILABLE FALSE)
    message(WARNING "GNU RISC-V assembler not found - parity tests disabled")
endif()

# Function: add_parity_test
# Assemble a single file with both assemblers and compare output
function(add_parity_test TEST_NAME ASM_FILE)
    if(NOT GNU_ASM_AVAILABLE OR NOT RV32AS_EXECUTABLE)
        return()
    endif()
    
    get_filename_component(ASM_BASENAME ${ASM_FILE} NAME_WE)
    get_filename_component(ASM_DIR ${ASM_FILE} DIRECTORY)
    get_filename_component(DIR_NAME ${ASM_DIR} NAME)
    
    set(RUST_OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/parity_${DIR_NAME}_${ASM_BASENAME}_rust.bin)
    set(GNU_OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/parity_${DIR_NAME}_${ASM_BASENAME}_gnu.bin)
    set(GNU_OBJECT ${CMAKE_CURRENT_BINARY_DIR}/parity_${DIR_NAME}_${ASM_BASENAME}_gnu.o)
    
    # Create a test that runs both assemblers and compares output
    add_test(
        NAME ${TEST_NAME}
        COMMAND ${CMAKE_COMMAND}
            -DRUST_ASSEMBLER=${RV32AS_EXECUTABLE}
            -DGNU_ASSEMBLER=${RISCV_AS}
            -DOBJ_COPY=${RISCV_OBJCOPY}
            -DINPUT_ASM=${ASM_FILE}
            -DRUST_OUTPUT=${RUST_OUTPUT}
            -DGNU_OUTPUT=${GNU_OUTPUT}
            -DGNU_OBJECT=${GNU_OBJECT}
            -DTEST_NAME=${DIR_NAME}/${ASM_BASENAME}
            -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/RunParityTest.cmake
    )
    
    set_tests_properties(${TEST_NAME} PROPERTIES
        LABELS "parity;phase_d1"
        TIMEOUT 30
        FIXTURES_REQUIRED rv32as_built
    )
endfunction()

# Function: add_c_parity_test
# Compile C -> assembly with GCC, then assemble with both assemblers and compare .text
function(add_c_parity_test TEST_NAME C_FILE MARCH MABI)
    if(NOT GNU_ASM_AVAILABLE OR NOT RV32AS_EXECUTABLE OR NOT RISCV_GCC OR NOT PYTHON_EXECUTABLE)
        return()
    endif()

    get_filename_component(C_BASENAME ${C_FILE} NAME_WE)
    get_filename_component(C_DIR ${C_FILE} DIRECTORY)
    get_filename_component(DIR_NAME ${C_DIR} NAME)

    set(RUST_OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/parity_c_${DIR_NAME}_${C_BASENAME}_rust.o)
    set(GNU_OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/parity_c_${DIR_NAME}_${C_BASENAME}_gnu.bin)
    set(GNU_OBJECT ${CMAKE_CURRENT_BINARY_DIR}/parity_c_${DIR_NAME}_${C_BASENAME}_gnu.o)
    set(GCC_ASM ${CMAKE_CURRENT_BINARY_DIR}/parity_c_${DIR_NAME}_${C_BASENAME}_gcc.s)
    set(NORMALIZED_ASM ${CMAKE_CURRENT_BINARY_DIR}/parity_c_${DIR_NAME}_${C_BASENAME}_normalized.s)
    set(PREPROCESS_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/cmake/preprocess_gcc_for_parity.py)

    add_test(
        NAME ${TEST_NAME}
        COMMAND ${CMAKE_COMMAND}
            -DRUST_ASSEMBLER=${RV32AS_EXECUTABLE}
            -DGNU_ASSEMBLER=${RISCV_AS}
            -DGNU_GCC=${RISCV_GCC}
            -DLINKER=${RISCV_LD}
            -DLINKER_SCRIPT=${CMAKE_CURRENT_SOURCE_DIR}/linker.ld
            -DC_PARITY_COMPARE_LINKED=OFF
            -DOBJ_COPY=${RISCV_OBJCOPY}
            -DPYTHON_EXECUTABLE=${PYTHON_EXECUTABLE}
            -DPREPROCESS_SCRIPT=${PREPROCESS_SCRIPT}
            -DINPUT_C=${C_FILE}
            -DMARCH=${MARCH}
            -DMABI=${MABI}
            -DGCC_ASM=${GCC_ASM}
            -DNORMALIZED_ASM=${NORMALIZED_ASM}
            -DRUST_OUTPUT=${RUST_OUTPUT}
            -DGNU_OUTPUT=${GNU_OUTPUT}
            -DGNU_OBJECT=${GNU_OBJECT}
            -DTEST_NAME=${DIR_NAME}/${C_BASENAME}
            -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/RunCParityTest.cmake
    )

    set_tests_properties(${TEST_NAME} PROPERTIES
        LABELS "parity;phase_d1;c_parity"
        TIMEOUT 60
        FIXTURES_REQUIRED rv32as_built
    )
endfunction()
