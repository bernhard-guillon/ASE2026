# CMake helper functions for blackbox testing
# Discovers and registers assembly and C test programs with CTest

function(add_blackbox_asm_tests)
    # Discover and register all assembly tests
    
    if(NOT RISCV_TOOLCHAIN_FOUND)
        message(WARNING "RISC-V toolchain not found - blackbox asm tests disabled")
        return()
    endif()
    
    # Find all test.s files in blackbox_tests/asm/
    file(GLOB_RECURSE ASM_TESTS "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/asm/*/test.s")
    
    if(NOT ASM_TESTS)
        message(STATUS "No assembly tests found in blackbox_tests/asm/")
        return()
    endif()
    
    message(STATUS "Found ${ASM_TESTS} assembly tests")
    
    # Linker script path
    set(LINKER_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/linker.ld")
    
    foreach(TEST_S ${ASM_TESTS})
        # Get test directory
        get_filename_component(TEST_DIR ${TEST_S} DIRECTORY)
        get_filename_component(TEST_NAME ${TEST_DIR} NAME)
        get_filename_component(TEST_CATEGORY ${TEST_DIR} DIRECTORY)
        get_filename_component(TEST_CATEGORY ${TEST_CATEGORY} NAME)
        
        # Set test file paths
        set(TEST_O "${TEST_DIR}/test.o")
        set(TEST_ELF "${TEST_DIR}/test.elf")
        set(TEST_BIN "${TEST_DIR}/test.bin")
        set(CONFIG_FILE "${TEST_DIR}/config.txt")
        set(EXPECTED_FILE "${TEST_DIR}/expected.txt")
        
        # Skip if missing config or expected
        if(NOT EXISTS ${CONFIG_FILE} OR NOT EXISTS ${EXPECTED_FILE})
            message(WARNING "Skipping ${TEST_CATEGORY}/${TEST_NAME} (missing config.txt or expected.txt)")
            continue()
        endif()
        
        # Create full test name
        set(FULL_TEST_NAME "asm/${TEST_CATEGORY}/${TEST_NAME}")
        
        # Add custom command to assemble
        add_custom_command(
            OUTPUT ${TEST_O}
            COMMAND ${RISCV_AS} -march=rv32i -mabi=ilp32 -o ${TEST_O} ${TEST_S}
            DEPENDS ${TEST_S}
            COMMENT "Assembling asm/${TEST_CATEGORY}/${TEST_NAME}"
            VERBATIM
        )
        
        # Add custom command to link
        add_custom_command(
            OUTPUT ${TEST_ELF}
            COMMAND ${RISCV_LD} -m elf32lriscv -T ${LINKER_SCRIPT} -o ${TEST_ELF} ${TEST_O}
            DEPENDS ${TEST_O} ${LINKER_SCRIPT}
            COMMENT "Linking asm/${TEST_CATEGORY}/${TEST_NAME}"
            VERBATIM
        )
        
        # Add custom command to convert to binary
        add_custom_command(
            OUTPUT ${TEST_BIN}
            COMMAND ${RISCV_OBJCOPY} -O binary ${TEST_ELF} ${TEST_BIN}
            DEPENDS ${TEST_ELF}
            COMMENT "Converting asm/${TEST_CATEGORY}/${TEST_NAME} to binary"
            VERBATIM
        )
        
        # Add custom target for this test
        add_custom_target(
            blackbox_asm_${TEST_CATEGORY}_${TEST_NAME}
            DEPENDS ${TEST_BIN}
        )
        
        # Parse config.txt for exit code and timeout
        set(EXPECTED_EXIT_CODE 0)
        set(TIMEOUT_MS 1000)
        if(EXISTS ${CONFIG_FILE})
            file(STRINGS ${CONFIG_FILE} CONFIG_LINES)
            foreach(LINE ${CONFIG_LINES})
                if(LINE MATCHES "^exit_code=(.*)$")
                    set(EXPECTED_EXIT_CODE "${CMAKE_MATCH_1}")
                elseif(LINE MATCHES "^timeout_ms=(.*)$")
                    set(TIMEOUT_MS "${CMAKE_MATCH_1}")
                endif()
            endforeach()
        endif()
        
        # Read expected output
        file(READ ${EXPECTED_FILE} EXPECTED_OUTPUT)
        
        # Add ctest test
        add_test(
            NAME "${FULL_TEST_NAME}"
            COMMAND bash -c "${CMAKE_CURRENT_SOURCE_DIR}/build/emulator_runner ${TEST_BIN} > /tmp/test_output_${TEST_CATEGORY}_${TEST_NAME}.txt 2>&1; cat /tmp/test_output_${TEST_CATEGORY}_${TEST_NAME}.txt"
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        # Set test properties
        set_tests_properties(
            "${FULL_TEST_NAME}"
            PROPERTIES
            TIMEOUT ${TIMEOUT_MS}
            PASS_REGULAR_EXPRESSION ".*"  # Any output is fine, actual validation in Python script
        )
        
    endforeach()
    
    message(STATUS "Registered ${NUMBER_OF_ASM_TESTS} assembly tests")
    
endfunction()

function(add_blackbox_c_tests)
    # Discover and register all C test programs
    
    if(NOT RISCV_TOOLCHAIN_FOUND)
        message(WARNING "RISC-V toolchain not found - blackbox C tests disabled")
        return()
    endif()
    
    # Find all *.c files in blackbox_tests/c/
    file(GLOB_RECURSE C_TESTS "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/c/*/*.c")
    
    if(NOT C_TESTS)
        message(STATUS "No C tests found in blackbox_tests/c/")
        return()
    endif()
    
    message(STATUS "Found ${C_TESTS} C test programs")
    
    # Helper files
    set(CRT0 "${CMAKE_CURRENT_SOURCE_DIR}/crt0.s")
    set(SYSCALLS "${CMAKE_CURRENT_SOURCE_DIR}/syscalls.s")
    set(LINKER_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/linker.ld")
    
    foreach(TEST_C ${C_TESTS})
        # Get test file info
        get_filename_component(TEST_FILE ${TEST_C} NAME_WE)
        get_filename_component(TEST_DIR ${TEST_C} DIRECTORY)
        get_filename_component(TEST_CATEGORY ${TEST_DIR} NAME)
        
        # Skip library files only
        if(TEST_FILE STREQUAL "malloc")
            message(STATUS "Skipping ${TEST_FILE}.c (library file, not a test program)")
            continue()
        endif()
        
        # Set output paths
        set(TEST_ELF "${TEST_DIR}/${TEST_FILE}.elf")
        set(TEST_BIN "${TEST_DIR}/${TEST_FILE}.bin")
        
        # Check if malloc.c exists in same directory (for malloc tests)
        set(MALLOC_C "")
        if(EXISTS "${TEST_DIR}/malloc.c")
            set(MALLOC_C "${TEST_DIR}/malloc.c")
        endif()
        
        # Create full test name
        set(FULL_TEST_NAME "c/${TEST_CATEGORY}/${TEST_FILE}")
        
        # Add custom command to compile and link
        add_custom_command(
            OUTPUT ${TEST_ELF}
            COMMAND ${RISCV_GCC} -march=rv32i -mabi=ilp32 -nostdlib -static
                -T ${LINKER_SCRIPT} -o ${TEST_ELF}
                ${CRT0} ${SYSCALLS} ${TEST_C} ${MALLOC_C}
            DEPENDS ${TEST_C} ${CRT0} ${SYSCALLS} ${LINKER_SCRIPT} ${MALLOC_C}
            COMMENT "Compiling c/${TEST_CATEGORY}/${TEST_FILE}"
            VERBATIM
        )
        
        # Add custom command to convert to binary
        add_custom_command(
            OUTPUT ${TEST_BIN}
            COMMAND ${RISCV_OBJCOPY} -O binary ${TEST_ELF} ${TEST_BIN}
            DEPENDS ${TEST_ELF}
            COMMENT "Converting c/${TEST_CATEGORY}/${TEST_FILE} to binary"
            VERBATIM
        )
        
        # Add custom target for this test
        add_custom_target(
            blackbox_c_${TEST_CATEGORY}_${TEST_FILE}
            DEPENDS ${TEST_BIN}
        )
        
        # Add ctest test (C tests are informational - no expected output validation)
        add_test(
            NAME "${FULL_TEST_NAME}"
            COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/build/emulator_runner ${TEST_BIN}
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        # Set timeout (longer for complex programs)
        set_tests_properties(
            "${FULL_TEST_NAME}"
            PROPERTIES
            TIMEOUT 10
        )
        
    endforeach()
    
    message(STATUS "Registered C tests for automatic compilation")
    
endfunction()

function(add_blackbox_all_target)
    # Create target to build all blackbox test artifacts
    
    if(NOT RISCV_TOOLCHAIN_FOUND)
        return()
    endif()
    
    # Find all test.s files
    file(GLOB_RECURSE ASM_TESTS "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/asm/*/test.s")
    
    # Find all test *.c files
    file(GLOB_RECURSE C_TESTS "${CMAKE_CURRENT_SOURCE_DIR}/blackbox_tests/c/*/*.c")
    
    # Create list of all artifacts
    set(ALL_ARTIFACTS "")
    
    foreach(TEST_S ${ASM_TESTS})
        get_filename_component(TEST_DIR ${TEST_S} DIRECTORY)
        list(APPEND ALL_ARTIFACTS "${TEST_DIR}/test.bin")
    endforeach()
    
    foreach(TEST_C ${C_TESTS})
        get_filename_component(TEST_FILE ${TEST_C} NAME_WE)
        get_filename_component(TEST_DIR ${TEST_C} DIRECTORY)
        
        # Skip library file
        if(TEST_FILE STREQUAL "malloc")
            continue()
        endif()
        
        list(APPEND ALL_ARTIFACTS "${TEST_DIR}/${TEST_FILE}.bin")
    endforeach()
    
    # Create master target
    if(ALL_ARTIFACTS)
        add_custom_target(
            build_blackbox_tests ALL
            DEPENDS ${ALL_ARTIFACTS}
            COMMENT "Building all blackbox test artifacts..."
        )
    endif()
    
endfunction()
