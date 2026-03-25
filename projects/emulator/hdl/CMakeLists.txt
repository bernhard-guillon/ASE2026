# HDL (Verilog) Build Integration
# Adds Verilator simulation target to the emulator project

# Check for Verilator
find_program(VERILATOR verilator)

if(VERILATOR)
    message(STATUS "Found Verilator: ${VERILATOR}")
    
    # Get Verilator include directory
    execute_process(
        COMMAND ${VERILATOR} --getenv VERILATOR_ROOT
        OUTPUT_VARIABLE VERILATOR_ROOT
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    
    # HDL source files
    set(HDL_RTL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/rtl)
    set(HDL_TB_DIR ${CMAKE_CURRENT_SOURCE_DIR}/tb)
    set(HDL_SIM_DIR ${CMAKE_CURRENT_SOURCE_DIR}/sim)
    
    set(VERILOG_SOURCES
        ${HDL_RTL_DIR}/emulator_top.v
        ${HDL_RTL_DIR}/cpu.v
        ${HDL_RTL_DIR}/alu.v
        ${HDL_RTL_DIR}/fpu.v
        ${HDL_RTL_DIR}/memory.v
    )
    
    set(VERILATOR_CPP_SOURCES
        ${HDL_TB_DIR}/verilator_runner.cpp
    )
    
    # Create custom target for Verilator build
    add_custom_target(verilator_runner ALL
        COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/verilator
        COMMAND ${VERILATOR}
            --cc --exe --build
            -Wall -Wno-fatal
            --trace
            -O3
            --top-module emulator_top
            -CFLAGS "-std=c++17"
            --Mdir ${CMAKE_CURRENT_BINARY_DIR}/verilator
            -o verilator_runner
            ${VERILOG_SOURCES}
            ${VERILATOR_CPP_SOURCES}
        COMMAND ${CMAKE_COMMAND} -E copy
            ${CMAKE_CURRENT_BINARY_DIR}/verilator/verilator_runner
            ${CMAKE_BINARY_DIR}/verilator_runner
        DEPENDS ${VERILOG_SOURCES} ${VERILATOR_CPP_SOURCES}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Building Verilator simulation model"
        VERBATIM
    )
    
    # Add lint target
    add_custom_target(verilator_lint
        COMMAND ${VERILATOR} --lint-only -Wall ${VERILOG_SOURCES}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Running Verilator lint"
        VERBATIM
    )
    
else()
    message(STATUS "Verilator not found - HDL simulation targets disabled")
    message(STATUS "Install Verilator to enable: pacman -S verilator (Arch) or apt install verilator (Ubuntu)")
endif()
