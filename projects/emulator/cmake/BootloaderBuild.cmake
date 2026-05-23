# Phase 5: CMake Bootloader Build System
#
# Provides CMake functions for automated model compilation and bootloader generation.
# Allows simple integration of models into the build system:
#
#   add_model_bootloader(generator_model "path/to/generator.json")
#
# This function automatically:
# 1. Detects the compile_model_bootloader.py script
# 2. Validates input JSON files at configure time
# 3. Adds custom build commands for compilation
# 4. Generates ELF and optionally binary outputs
# 5. Places outputs in ${CMAKE_BINARY_DIR}/bootloaders/ (out-of-tree)
# 6. Registers build targets for easy dependency management

include_guard()

# Find Python 3
find_package(Python3 COMPONENTS Interpreter REQUIRED)

# Locate compile_model_bootloader.py script
function(_find_bootloader_compiler)
    # Search in common locations
    set(SEARCH_PATHS
        "${CMAKE_CURRENT_SOURCE_DIR}/compile_model_bootloader.py"
        "${CMAKE_CURRENT_LIST_DIR}/../compile_model_bootloader.py"
        "${CMAKE_CURRENT_LIST_DIR}/../emulator/compile_model_bootloader.py"
    )
    
    foreach(path ${SEARCH_PATHS})
        if(EXISTS "${path}")
            set(BOOTLOADER_COMPILER "${path}" PARENT_SCOPE)
            return()
        endif()
    endforeach()
    
    message(FATAL_ERROR "Cannot find compile_model_bootloader.py. Searched: ${SEARCH_PATHS}")
endfunction()

# Locate bootloader.ld linker script
function(_find_linker_script)
    set(SEARCH_PATHS
        "${CMAKE_CURRENT_SOURCE_DIR}/bootloader.ld"
        "${CMAKE_CURRENT_LIST_DIR}/../bootloader.ld"
        "${CMAKE_CURRENT_LIST_DIR}/../emulator/bootloader.ld"
    )
    
    foreach(path ${SEARCH_PATHS})
        if(EXISTS "${path}")
            set(BOOTLOADER_LINKER_SCRIPT "${path}" PARENT_SCOPE)
            return()
        endif()
    endforeach()
    
    message(FATAL_ERROR "Cannot find bootloader.ld linker script. Searched: ${SEARCH_PATHS}")
endfunction()

# Initialize bootloader build system
function(bootloader_build_system_init)
    # Find scripts and tools (only once at config time)
    _find_bootloader_compiler()
    _find_linker_script()
    
    # Create output directory for bootloader artifacts
    set(BOOTLOADER_OUTPUT_DIR "${CMAKE_BINARY_DIR}/bootloaders")
    file(MAKE_DIRECTORY "${BOOTLOADER_OUTPUT_DIR}")
    
    # Set cache variables
    set(BOOTLOADER_COMPILER "${BOOTLOADER_COMPILER}" CACHE INTERNAL "Path to compile_model_bootloader.py")
    set(BOOTLOADER_LINKER_SCRIPT "${BOOTLOADER_LINKER_SCRIPT}" CACHE INTERNAL "Path to bootloader.ld")
    set(BOOTLOADER_OUTPUT_DIR "${BOOTLOADER_OUTPUT_DIR}" CACHE INTERNAL "Bootloader output directory")
    
    message(STATUS "Bootloader Build System Initialized")
    message(STATUS "  Compiler: ${BOOTLOADER_COMPILER}")
    message(STATUS "  Linker:   ${BOOTLOADER_LINKER_SCRIPT}")
    message(STATUS "  Output:   ${BOOTLOADER_OUTPUT_DIR}")
endfunction()

# Add a model bootloader build target
#
# Usage:
#   add_model_bootloader(target_name "path/to/model.json")
#
# Arguments:
#   target_name: Name for the build target (e.g., "generator_bootloader")
#   json_file:   Path to model JSON file (absolute or relative to CMAKE_CURRENT_SOURCE_DIR)
#   BINARY:      (Optional) Generate binary file in addition to ELF
#   VERBOSE:     (Optional) Enable verbose output from compiler
#
# Outputs:
#   ${CMAKE_BINARY_DIR}/bootloaders/<model_name>.elf
#   ${CMAKE_BINARY_DIR}/bootloaders/<model_name>.bin (if BINARY flag used)
#
# Creates CMake targets:
#   <target_name>       - Builds the bootloader
#   <target_name>_elf   - Returns path to ELF file
#   <target_name>_bin   - Returns path to binary file (if generated)
#
function(add_model_bootloader target_name json_file)
    set(options BINARY VERBOSE)
    cmake_parse_arguments(BOOTLOADER "${options}" "" "" ${ARGN})
    
    # Resolve JSON file path
    if(IS_ABSOLUTE "${json_file}")
        set(json_abs "${json_file}")
    else()
        set(json_abs "${CMAKE_CURRENT_SOURCE_DIR}/${json_file}")
    endif()
    
    # Validate JSON file exists
    if(NOT EXISTS "${json_abs}")
        message(FATAL_ERROR "Model JSON file not found: ${json_abs}")
    endif()
    
    # Extract model name from JSON filename
    get_filename_component(model_name "${json_abs}" NAME_WE)
    
    # Set output paths (out-of-tree in build directory)
    set(elf_file "${BOOTLOADER_OUTPUT_DIR}/${model_name}.elf")
    
    # Build command
    set(compile_cmd
        "${Python3_EXECUTABLE}" "${BOOTLOADER_COMPILER}"
        "${json_abs}"
        "--output" "${elf_file}"
    )
    
    # Optional binary output
    if(BOOTLOADER_BINARY)
        set(bin_file "${BOOTLOADER_OUTPUT_DIR}/${model_name}.bin")
        list(APPEND compile_cmd "--binary" "${bin_file}")
    else()
        set(bin_file "")
    endif()
    
    # Optional verbose mode
    if(BOOTLOADER_VERBOSE)
        list(APPEND compile_cmd "--verbose")
    endif()
    
    # Create custom build target
    add_custom_command(
        OUTPUT "${elf_file}" ${bin_file}
        COMMAND ${compile_cmd}
        DEPENDS "${json_abs}" "${BOOTLOADER_COMPILER}" "${BOOTLOADER_LINKER_SCRIPT}"
        COMMENT "Building bootloader for ${model_name}..."
        VERBATIM
    )
    
    # Create build target
    add_custom_target(
        "${target_name}" ALL
        DEPENDS "${elf_file}" ${bin_file}
    )
    
    # Set target properties for easy access
    set_target_properties("${target_name}" PROPERTIES
        BOOTLOADER_MODEL_NAME "${model_name}"
        BOOTLOADER_ELF_FILE "${elf_file}"
        BOOTLOADER_BIN_FILE "${bin_file}"
        BOOTLOADER_JSON_FILE "${json_abs}"
    )
    
    # Log success
    if(BOOTLOADER_BINARY)
        message(STATUS "Bootloader target '${target_name}' configured")
        message(STATUS "  Model:  ${json_abs}")
        message(STATUS "  ELF:    ${elf_file}")
        message(STATUS "  Binary: ${bin_file}")
    else()
        message(STATUS "Bootloader target '${target_name}' configured")
        message(STATUS "  Model: ${json_abs}")
        message(STATUS "  ELF:   ${elf_file}")
    endif()
endfunction()

# Get ELF file path from bootloader target
#
# Usage:
#   get_bootloader_elf_file(target_name output_variable)
#
function(get_bootloader_elf_file target_name output_variable)
    get_target_property(elf_file "${target_name}" BOOTLOADER_ELF_FILE)
    if(NOT elf_file)
        message(FATAL_ERROR "Target '${target_name}' is not a bootloader target")
    endif()
    set("${output_variable}" "${elf_file}" PARENT_SCOPE)
endfunction()

# Get binary file path from bootloader target
#
# Usage:
#   get_bootloader_bin_file(target_name output_variable)
#
function(get_bootloader_bin_file target_name output_variable)
    get_target_property(bin_file "${target_name}" BOOTLOADER_BIN_FILE)
    if(NOT bin_file)
        message(FATAL_ERROR "Target '${target_name}' does not have a binary file")
    endif()
    set("${output_variable}" "${bin_file}" PARENT_SCOPE)
endfunction()

# Get model name from bootloader target
#
# Usage:
#   get_bootloader_model_name(target_name output_variable)
#
function(get_bootloader_model_name target_name output_variable)
    get_target_property(model_name "${target_name}" BOOTLOADER_MODEL_NAME)
    if(NOT model_name)
        message(FATAL_ERROR "Target '${target_name}' is not a bootloader target")
    endif()
    set("${output_variable}" "${model_name}" PARENT_SCOPE)
endfunction()
