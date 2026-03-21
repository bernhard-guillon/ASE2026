#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include "elf_loader.h"

int main() {
    // Load static_char_gen.elf
    std::ifstream file("static_char_gen.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    // Parse ELF
    auto segments = ElfLoader::parseElf(buffer);
    
    std::cout << "Loaded " << segments.size() << " segments:" << std::endl;
    for (size_t i = 0; i < segments.size(); ++i) {
        const auto& seg = segments[i];
        std::cout << "  Segment " << i << ":" << std::endl;
        std::cout << "    VMA: 0x" << std::hex << seg.vaddr << std::dec << std::endl;
        std::cout << "    Size: 0x" << std::hex << seg.size << std::dec << " (" << seg.size << " bytes)" << std::endl;
        std::cout << "    Data size: " << seg.data.size() << " bytes" << std::endl;
        
        // Check what's at offset 0x130 in the segment
        if (0x130 < seg.data.size()) {
            std::cout << "    Data at offset 0x130: ";
            for (int j = 0; j < 8; ++j) {
                std::cout << std::hex << (int)seg.data[0x130 + j] << " ";
            }
            std::cout << std::dec << std::endl;
        }
        
        // Check what's at offset 0xa0
        if (0xa0 < seg.data.size()) {
            std::cout << "    Data at offset 0xa0: ";
            for (int j = 0; j < 8; ++j) {
                std::cout << std::hex << (int)seg.data[0xa0 + j] << " ";
            }
            std::cout << std::dec << std::endl;
        }
    }
    
    return 0;
}
