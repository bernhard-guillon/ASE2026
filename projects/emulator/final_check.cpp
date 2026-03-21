#include <iostream>
#include <fstream>
#include <vector>
#include "elf_loader.h"

int main() {
    std::ifstream file("static_char_gen.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    std::cout << "Loaded " << size << " bytes from static_char_gen.elf" << std::endl;
    
    // Use the actual ELF loader
    auto segments = ElfLoader::parseElf(buffer);
    
    std::cout << "Parsed " << segments.size() << " segment(s)" << std::endl;
    
    for (size_t i = 0; i < segments.size(); ++i) {
        const auto& seg = segments[i];
        std::cout << "\nSegment " << i << ":" << std::endl;
        std::cout << "  VMA: 0x" << std::hex << seg.vaddr << std::dec << std::endl;
        std::cout << "  Size: " << seg.size << std::endl;
        std::cout << "  Data size: " << seg.data.size() << std::endl;
        
        // Check specific bytes
        if (seg.data.size() > 0x130 + 8) {
            std::cout << "  Bytes at segment offset 0x130: ";
            for (int j = 0; j < 8; ++j) {
                std::cout << std::hex << (int)seg.data[0x130 + j] << " ";
            }
            std::cout << std::dec << std::endl;
        }
        
        if (seg.data.size() > 0xa0 + 8) {
            std::cout << "  Bytes at segment offset 0xa0: ";
            for (int j = 0; j < 8; ++j) {
                std::cout << std::hex << (int)seg.data[0xa0 + j] << " ";
            }
            std::cout << std::dec << std::endl;
        }
    }
    
    return 0;
}
