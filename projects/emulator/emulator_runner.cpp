#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include "Emulator.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <binary_file>" << std::endl;
        return 1;
    }
    
    bool verbose = false;
    const char* binary_file = argv[1];
    
    // Check for --verbose flag
    for (int i = 2; i < argc; ++i) {
        if (std::strcmp(argv[i], "--verbose") == 0 || std::strcmp(argv[i], "-v") == 0) {
            verbose = true;
        }
    }
    
    // Read binary file
    std::ifstream file(binary_file, std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "Error: Could not open file " << binary_file << std::endl;
        return 1;
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<uint8_t> buffer(size);
    if (!file.read(reinterpret_cast<char*>(buffer.data()), size)) {
        std::cerr << "Error: Could not read file" << std::endl;
        return 1;
    }
    
    if (verbose) {
        std::cout << "Loaded " << size << " bytes from " << binary_file << std::endl;
    }
    
    // Create emulator with 1GB memory (for mmap and dynamic allocation)
    Emulator emulator(1024 * 1024 * 1024);
    
    // Load binary into memory at address 0
    for (size_t i = 0; i < buffer.size(); ++i) {
        emulator.getMemory().write8(i, buffer[i]);
    }
    
    // Initialize stack pointer to 512MB (high in address space for stack growth)
    emulator.getCPU().setReg(2, 512 * 1024 * 1024);
    
    if (verbose) {
        std::cout << "Program loaded at address 0" << std::endl;
        std::cout << "Starting execution..." << std::endl;
        std::cout << "----------------------------------------" << std::endl;
    }
    
    // Run the program
    try {
        emulator.run(1000000);  // Max 1M instructions (for recursive functions)
        
        if (verbose) {
            std::cout << "----------------------------------------" << std::endl;
            if (emulator.isHalted()) {
                std::cout << "Program exited normally" << std::endl;
            } else {
                std::cout << "Program reached instruction limit" << std::endl;
            }
            std::cout << "Final PC: 0x" << std::hex << emulator.getCPU().getPC() << std::endl;
        }
        
        // Return the program's exit code
        return emulator.getExitCode();
        
    } catch (const std::exception& e) {
        std::cerr << "Error during execution: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
