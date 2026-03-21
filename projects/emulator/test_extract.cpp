#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include <cstdint>

int main() {
    std::ifstream file("static_char_gen.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    uint32_t p_offset = 0x1000;
    uint32_t p_filesz = 102160;
    
    std::cout << "Extracting from buffer[0x" << std::hex << p_offset << "] to buffer[0x"
              << (p_offset + p_filesz) << std::dec << "]" << std::endl;
    
    // Direct check - what's in buffer at offset 0x1130?
    std::cout << "\nDirect check - buffer[0x1130 to 0x1140]:" << std::endl;
    for (int i = 0; i < 16; ++i) {
        std::cout << std::hex << (int)buffer[0x1130 + i] << " ";
    }
    std::cout << std::dec << std::endl;
    
    // Extract like the ELF loader does
    std::vector<uint8_t> data(buffer.begin() + p_offset,
                             buffer.begin() + p_offset + p_filesz);
    
    std::cout << "\nExtracted data[0x130 to 0x140]:" << std::endl;
    for (int i = 0; i < 16; ++i) {
        std::cout << std::hex << (int)data[0x130 + i] << " ";
    }
    std::cout << std::dec << std::endl;
    
    // Also check data[0x0 to 0x10]
    std::cout << "\nExtracted data[0x0 to 0x10]:" << std::endl;
    for (int i = 0; i < 16; ++i) {
        std::cout << std::hex << (int)data[0x0 + i] << " ";
    }
    std::cout << std::dec << std::endl;
    
    return 0;
}
