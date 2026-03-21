#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include <cstdint>

int main() {
    // Load static_char_gen.elf
    std::ifstream file("static_char_gen.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    std::cout << "File size: " << size << std::endl;
    
    // Parse ELF header
    uint32_t e_phoff, e_phentsize;
    uint16_t e_phnum;
    
    std::memcpy(&e_phoff, &buffer[28], 4);
    std::memcpy(&e_phentsize, &buffer[42], 2);
    std::memcpy(&e_phnum, &buffer[44], 2);
    
    std::cout << "Program header offset: 0x" << std::hex << e_phoff << std::dec << std::endl;
    std::cout << "Program header entry size: " << e_phentsize << std::endl;
    std::cout << "Number of program headers: " << e_phnum << std::endl;
    
    // Read first program header
    if (e_phnum > 0) {
        uint32_t ph_offset = e_phoff;
        uint32_t p_type, p_offset, p_vaddr, p_filesz, p_memsz;
        
        std::memcpy(&p_type, &buffer[ph_offset + 0], 4);
        std::memcpy(&p_offset, &buffer[ph_offset + 4], 4);
        std::memcpy(&p_vaddr, &buffer[ph_offset + 8], 4);
        std::memcpy(&p_filesz, &buffer[ph_offset + 16], 4);
        std::memcpy(&p_memsz, &buffer[ph_offset + 20], 4);
        
        std::cout << "\nFirst PT_LOAD segment:" << std::endl;
        std::cout << "  Type: " << p_type << std::endl;
        std::cout << "  File offset: 0x" << std::hex << p_offset << std::dec << std::endl;
        std::cout << "  VMA: 0x" << std::hex << p_vaddr << std::dec << std::endl;
        std::cout << "  File size: 0x" << std::hex << p_filesz << std::dec << std::endl;
        std::cout << "  Memory size: 0x" << std::hex << p_memsz << std::dec << std::endl;
        
        // Check data at file offset
        if (p_offset + 16 <= buffer.size()) {
            std::cout << "\nFirst 16 bytes at file offset 0x" << std::hex << p_offset << std::dec << ":" << std::endl;
            for (int i = 0; i < 16; ++i) {
                std::cout << std::hex << (int)buffer[p_offset + i] << " ";
            }
            std::cout << std::dec << std::endl;
        }
        
        // Check data at offset 0x130 from p_offset
        if (p_offset + 0x130 + 16 <= buffer.size()) {
            std::cout << "\nFirst 16 bytes at file offset 0x" << std::hex << (p_offset + 0x130) << std::dec << ":" << std::endl;
            for (int i = 0; i < 16; ++i) {
                std::cout << std::hex << (int)buffer[p_offset + 0x130 + i] << " ";
            }
            std::cout << std::dec << std::endl;
        }
    }
    
    return 0;
}
