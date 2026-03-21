#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include "Emulator.h"
#include "elf_loader.h"

int main() {
    // Load static_char_gen.elf
    std::ifstream file("static_char_gen.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    Emulator emulator(1024 * 1024 * 1024);
    
    // Load ELF
    auto segments = ElfLoader::parseElf(buffer);
    std::cout << "Loaded " << segments.size() << " segments:" << std::endl;
    for (const auto& seg : segments) {
        std::cout << "  Segment at 0x" << std::hex << seg.vaddr << std::dec 
                  << " size 0x" << std::hex << seg.size << std::dec 
                  << " data " << seg.data.size() << " bytes" << std::endl;
        
        for (size_t i = 0; i < seg.data.size(); ++i) {
            emulator.getMemory().write8(seg.vaddr + i, seg.data[i]);
        }
        for (size_t i = seg.data.size(); i < seg.size; ++i) {
            emulator.getMemory().write8(seg.vaddr + i, 0);
        }
    }
    
    // Check what's at 0xa0 (should be start of .rodata/char_images)
    std::cout << "\nFirst 50 bytes at 0xa0 (start of .rodata):" << std::endl;
    int nonzero = 0;
    for (int i = 0; i < 50; ++i) {
        uint8_t val = emulator.getMemory().read8(0xa0 + i);
        std::cout << std::hex << (int)val << " ";
        if (val != 0) nonzero++;
    }
    std::cout << "\nNon-zero: " << nonzero << std::endl;
    
    // Check offset in the .rodata file
    std::cout << "\n.rodata starts at file offset 0x10a0, size 0x18e70" << std::endl;
    std::cout << "First 50 bytes in ELF file at offset 0x10a0:" << std::endl;
    nonzero = 0;
    for (int i = 0; i < 50; ++i) {
        uint8_t val = buffer[0x10a0 + i];
        std::cout << std::hex << (int)val << " ";
        if (val != 0) nonzero++;
    }
    std::cout << "\nNon-zero: " << nonzero << std::endl;
    
    return 0;
}
