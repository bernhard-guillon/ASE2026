#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include "Emulator.h"
#include "elf_loader.h"

int main() {
    // Load test program
    std::ifstream file("test_char_access.elf", std::ios::binary | std::ios::ate);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);
    
    Emulator emulator(1024 * 1024 * 1024);
    
    // Load ELF
    auto segments = ElfLoader::parseElf(buffer);
    for (const auto& seg : segments) {
        for (size_t i = 0; i < seg.data.size(); ++i) {
            emulator.getMemory().write8(seg.vaddr + i, seg.data[i]);
        }
        for (size_t i = seg.data.size(); i < seg.size; ++i) {
            emulator.getMemory().write8(seg.vaddr + i, 0);
        }
    }
    
    uint32_t entry = ElfLoader::getEntryPoint(buffer);
    emulator.getCPU().setPC(entry);
    
    // Run emulator
    emulator.getCPU().setReg(2, 512 * 1024 * 1024);  // SP
    for (int i = 0; i < 100000; ++i) {
        emulator.step();
        if (emulator.getCPU().getPC() == entry || emulator.isHalted()) break;
    }
    
    // Check memory at framebuffer address
    std::cout << "Framebuffer values at 0x20000:" << std::endl;
    for (int i = 0; i < 15; ++i) {
        uint8_t val = emulator.getMemory().read8(0x20000 + i);
        std::cout << "  [0x" << std::hex << (0x20000 + i) << std::dec << "] = " 
                  << (int)val << std::endl;
    }
    
    return 0;
}
