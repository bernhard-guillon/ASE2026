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
    
    std::cout << "Loaded " << size << " bytes" << std::endl;
    
    // Parse ELF header manually
    uint32_t e_phoff, e_phentsize;
    uint16_t e_phnum;
    
    std::memcpy(&e_phoff, &buffer[28], 4);
    std::memcpy(&e_phentsize, &buffer[42], 2);
    std::memcpy(&e_phnum, &buffer[44], 2);
    
    // Find PT_LOAD segments
    for (int i = 0; i < e_phnum; ++i) {
        uint32_t ph_offset = e_phoff + i * e_phentsize;
        uint32_t p_type, p_offset, p_vaddr, p_filesz, p_memsz;
        
        std::memcpy(&p_type, &buffer[ph_offset + 0], 4);
        std::memcpy(&p_offset, &buffer[ph_offset + 4], 4);
        std::memcpy(&p_vaddr, &buffer[ph_offset + 8], 4);
        std::memcpy(&p_filesz, &buffer[ph_offset + 16], 4);
        std::memcpy(&p_memsz, &buffer[ph_offset + 20], 4);
        
        if (p_type == 1) {  // PT_LOAD
            std::cout << "\nPT_LOAD segment " << i << ":" << std::endl;
            std::cout << "  p_offset: 0x" << std::hex << p_offset << std::dec << std::endl;
            std::cout << "  p_filesz: " << p_filesz << std::endl;
            std::cout << "  p_vaddr: 0x" << std::hex << p_vaddr << std::dec << std::endl;
            
            // Check bounds
            if (p_offset + p_filesz <= buffer.size()) {
                std::cout << "  Bounds OK" << std::endl;
                
                // Extract data
                std::vector<uint8_t> data(buffer.begin() + p_offset,
                                         buffer.begin() + p_offset + p_filesz);
                
                std::cout << "  Extracted " << data.size() << " bytes" << std::endl;
                std::cout << "  First 16 bytes: ";
                for (int j = 0; j < 16 && j < data.size(); ++j) {
                    std::cout << std::hex << (int)data[j] << " ";
                }
                std::cout << std::dec << std::endl;
                
                // Check offset 0xa0
                if (0xa0 < data.size()) {
                    std::cout << "  Bytes at offset 0xa0: ";
                    for (int j = 0; j < 16; ++j) {
                        std::cout << std::hex << (int)data[0xa0 + j] << " ";
                    }
                    std::cout << std::dec << std::endl;
                }
                
                // Check offset 0x130
                if (0x130 < data.size()) {
                    std::cout << "  Bytes at offset 0x130: ";
                    for (int j = 0; j < 16; ++j) {
                        std::cout << std::hex << (int)data[0x130 + j] << " ";
                    }
                    std::cout << std::dec << std::endl;
                }
            }
        }
    }
    
    return 0;
}
