#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include <unistd.h>
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
    std::cout << "Set a0 = 65 ('A')" << std::endl;
    
    // Execute 1000 instructions
    for (int i = 0; i < 1000; ++i) {
        try {
            emulator.step();
        } catch (...) {
            std::cout << "Exception at instruction " << i << std::endl;
            break;
        }
    }
    
    // Check framebuffer
    std::cout << "First 50 bytes of framebuffer at 0x20000:" << std::endl;
    int nonzero_count = 0;
    for (int i = 0; i < 50; ++i) {
        uint8_t val = emulator.getMemory().read8(0x20000 + i);
        if (val != 0) {
            nonzero_count++;
            std::cout << "[" << i << "] = " << (int)val << std::endl;
        }
    }
    std::cout << "Total non-zero bytes in first 50: " << nonzero_count << std::endl;
    
    // Also check what's at char_images + 65*400
    uint32_t char_a_addr = 0xa0 + 65 * 400;
    std::cout << "\nChar 'A' should be at offset " << (65 * 400) << " in .rodata" << std::endl;
    std::cout << "First 50 bytes of char_images[65]:" << std::endl;
    nonzero_count = 0;
    for (int i = 0; i < 50; ++i) {
        uint8_t val = emulator.getMemory().read8(char_a_addr + i);
        if (val != 0) {
            nonzero_count++;
            std::cout << "[" << i << "] = " << (int)val << std::endl;
        }
    }
    std::cout << "Total non-zero bytes in first 50: " << nonzero_count << std::endl;
    
    return 0;
}
