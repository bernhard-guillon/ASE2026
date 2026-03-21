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
    
    // Manually parse like ELF loader does
    uint32_t e_phoff, e_shoff;
    uint16_t e_phentsize, e_phnum, e_shentsize, e_shnum;
    
    std::memcpy(&e_phoff, &buffer[28], 4);
    std::memcpy(&e_shoff, &buffer[32], 4);
    std::memcpy(&e_phentsize, &buffer[42], 2);
    std::memcpy(&e_phnum, &buffer[44], 2);
    std::memcpy(&e_shentsize, &buffer[46], 2);
    std::memcpy(&e_shnum, &buffer[48], 2);
    
    std::cout << "e_phoff=" << e_phoff << ", e_phentsize=" << e_phentsize 
              << ", e_phnum=" << e_phnum << std::endl;
    std::cout << "e_shoff=" << e_shoff << ", e_shentsize=" << e_shentsize 
              << ", e_shnum=" << e_shnum << std::endl;
    
    // Now iterate like the ELF loader
    for (int i = 0; i < e_phnum; ++i) {
        uint32_t ph_offset = e_phoff + i * e_phentsize;
        std::cout << "\ni=" << i << ", ph_offset=0x" << std::hex << ph_offset << std::dec << std::endl;
        
        if (ph_offset + 32 > buffer.size()) {
            std::cout << "  Out of bounds" << std::endl;
            continue;
        }
        
        uint32_t p_type, p_offset, p_vaddr, p_filesz, p_memsz;
        std::memcpy(&p_type, &buffer[ph_offset + 0], 4);
        std::memcpy(&p_offset, &buffer[ph_offset + 4], 4);
        std::memcpy(&p_vaddr, &buffer[ph_offset + 8], 4);
        std::memcpy(&p_filesz, &buffer[ph_offset + 16], 4);
        std::memcpy(&p_memsz, &buffer[ph_offset + 20], 4);
        
        std::cout << "  p_type=" << p_type;
        if (p_type == 1) std::cout << " (PT_LOAD)";
        std::cout << std::endl;
        std::cout << "  p_offset=0x" << std::hex << p_offset << std::dec 
                  << ", p_filesz=" << p_filesz << std::endl;
        std::cout << "  p_vaddr=0x" << std::hex << p_vaddr << std::dec 
                  << ", p_memsz=" << p_memsz << std::endl;
        
        if (p_type == 1) {
            std::cout << "  -> This is PT_LOAD, would load" << std::endl;
            
            // Check bounds
            if (p_offset + p_filesz > buffer.size()) {
                std::cout << "  -> ERROR: Out of bounds! p_offset + p_filesz = 0x" 
                          << std::hex << (p_offset + p_filesz) << " > 0x" 
                          << buffer.size() << std::dec << std::endl;
            } else {
                std::cout << "  -> Bounds OK" << std::endl;
                // Extract data
                std::vector<uint8_t> data(buffer.begin() + p_offset,
                                         buffer.begin() + p_offset + p_filesz);
                std::cout << "  -> Extracted " << data.size() << " bytes" << std::endl;
                if (data.size() > 0x130) {
                    std::cout << "  -> Byte at offset 0x130: 0x" << std::hex << (int)data[0x130] << std::dec << std::endl;
                }
            }
        }
    }
    
    return 0;
}
