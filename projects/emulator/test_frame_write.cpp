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
    
    // Check framebuffer
    std::cout << "Framebuffer check at 0x20000:" << std::endl;
    int nonzero = 0;
    for (int i = 0; i < 400; ++i) {
        uint8_t val = emulator.getMemory().read8(0x20000 + i);
        if (val != 0) {
            nonzero++;
            if (nonzero <= 20) {
                std::cout << "  [" << i << "] = " << (int)val << std::endl;
            }
        }
    }
    std::cout << "Total non-zero bytes: " << nonzero << " / 400" << std::endl;
    
    if (nonzero == 0) {
        std::cout << "\nFramebuffer is empty! Program didn't write to 0x20000." << std::endl;
        
        // Check if char_images[65] is accessible
        std::cout << "\nChecking char_images[65] at 0xa0 + 65*400 = 0x" << std::hex << (0xa0 + 65*400) << std::dec << std::endl;
        int char_nonzero = 0;
        uint32_t char_addr = 0xa0 + 65 * 400;
        for (int i = 0; i < 50; ++i) {
            uint8_t val = emulator.getMemory().read8(char_addr + i);
            if (val != 0) {
                char_nonzero++;
                std::cout << "  [" << i << "] = " << (int)val << std::endl;
            }
        }
        std::cout << "Non-zero in first 50 bytes of char 65: " << char_nonzero << std::endl;
    }
    
    return 0;
}
