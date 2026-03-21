#include <iostream>
#include <fstream>
#include <vector>
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
    emulator.getCPU().setReg(2, 512 * 1024 * 1024);  // SP
    
    // Set a0 to 97 ('a')
    emulator.getCPU().setReg(10, 97);
    
    // Run 50000 instructions
    for (int i = 0; i < 50000; ++i) {
        try {
            emulator.step();
        } catch (...) {
            break;
        }
    }
    
    // Simple ASCII rendering
    std::cout << "Framebuffer (character 'a', using # for pixels, space for empty):" << std::endl;
    for (int row = 0; row < 20; ++row) {
        for (int col = 0; col < 20; ++col) {
            uint8_t pixel = emulator.getMemory().read8(0x20000 + row * 20 + col);
            std::cout << (pixel > 127 ? '#' : ' ');
        }
        std::cout << std::endl;
    }
    
    return 0;
}
