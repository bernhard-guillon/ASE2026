#include <iostream>
#include <fstream>
#include <vector>
#include "Emulator.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <binary_file>" << std::endl;
        return 1;
    }
    
    // Read binary file
    std::ifstream file(argv[1], std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "Error: Could not open file " << argv[1] << std::endl;
        return 1;
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<uint8_t> buffer(size);
    if (!file.read(reinterpret_cast<char*>(buffer.data()), size)) {
        std::cerr << "Error: Could not read file" << std::endl;
        return 1;
    }
    
    std::cout << "Loaded " << size << " bytes from " << argv[1] << std::endl;
    
    // Create emulator
    Emulator emulator(65536);
    
    // Load binary into memory at address 0
    for (size_t i = 0; i < buffer.size(); ++i) {
        emulator.getMemory().write8(i, buffer[i]);
    }
    
    std::cout << "Program loaded at address 0" << std::endl;
    std::cout << "Starting execution..." << std::endl;
    std::cout << "----------------------------------------" << std::endl;
    
    // Run the program
    try {
        emulator.run(10000);  // Max 10000 instructions
        
        std::cout << "----------------------------------------" << std::endl;
        if (emulator.isHalted()) {
            std::cout << "Program exited normally" << std::endl;
        } else {
            std::cout << "Program reached instruction limit" << std::endl;
        }
        std::cout << "Final PC: 0x" << std::hex << emulator.getCPU().getPC() << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error during execution: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
