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
    
    // Set a0 to 65 ('A')
    emulator.getCPU().setReg(10, 65);
    
    // Run 50000 instructions
    for (int i = 0; i < 50000; ++i) {
        try {
            emulator.step();
        } catch (...) {
            break;
        }
    }
    
    // Manually check what's at 0x20000
    std::cout << "Direct memory read at 0x20000:" << std::endl;
    int nonzero = 0;
    for (int i = 0; i < 20; ++i) {
        uint8_t val = emulator.getMemory().read8(0x20000 + i);
        std::cout << (int)val << " ";
        if (val != 0) nonzero++;
    }
    std::cout << std::endl;
    std::cout << "Non-zero in first 20 bytes: " << nonzero << std::endl;
    
    // Now test the renderer
    std::cout << "\nFramebuffer rendered:" << std::endl;
    FramebufferRenderer renderer;
    renderer.render(emulator.getMemory());
    
    return 0;
}
