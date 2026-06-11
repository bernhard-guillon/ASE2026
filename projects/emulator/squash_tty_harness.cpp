#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <iomanip>
#include "Emulator.h"
#include "elf_loader.h"

static constexpr uint32_t KEY_REG_ADDR = 0x154004;
static constexpr uint32_t DONE_FLAG_ADDR = 0x154000;
static constexpr uint32_t CYCLES_PER_FRAME = 50000;
static constexpr uint32_t FRAMES_PER_KEY = 3;  // enough frames for paddle to settle but game stays alive

static void dump_framebuffer_hex(Memory& mem) {
    std::cout << "FRAMEBUFFER_HEX:";
    for (uint32_t i = 0; i < FRAMEBUFFER_HEIGHT * FRAMEBUFFER_STRIDE; ++i) {
        uint8_t v = mem.read8(FRAMEBUFFER_ADDR + i);
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << static_cast<unsigned>(v);
    }
    std::cout << std::endl;
}

static void run_one_inference(Emulator& emu) {
    emu.getMemory().write32(DONE_FLAG_ADDR, 0);
    for (uint32_t i = 0; i < CYCLES_PER_FRAME; ++i) {
        emu.step();
        if (emu.isHalted()) break;
        if (emu.getMemory().read32(DONE_FLAG_ADDR) == 1) break;
    }
}

static void set_key(Emulator& emu, int key) {
    if (key < 0) return;
    uint32_t kc = static_cast<uint32_t>(key);
    for (uint32_t b = 0; b < 4; ++b) {
        emu.getMemory().write8(KEY_REG_ADDR + b,
            static_cast<uint8_t>((kc >> (b * 8)) & 0xFF));
    }
    emu.getCPU().setReg(10, kc);
    emu.getCPU().setReg(9, kc);
}

static void run_frames(Emulator& emu, int key, uint32_t n) {
    set_key(emu, key);
    for (uint32_t f = 0; f < n; ++f) {
        run_one_inference(emu);
    }
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <squash.elf>" << std::endl;
        return 1;
    }

    std::ifstream file(argv[1], std::ios::binary | std::ios::ate);
    if (!file) { std::cerr << "Cannot open " << argv[1] << std::endl; return 1; }
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);

    Emulator emu(1024 * 1024 * 1024);

    if (ElfLoader::validateElf(buffer)) {
        auto segments = ElfLoader::parseElf(buffer);
        for (const auto& seg : segments) {
            for (size_t i = 0; i < seg.data.size(); ++i)
                emu.getMemory().write8(seg.vaddr + i, seg.data[i]);
            for (size_t i = seg.data.size(); i < seg.size; ++i)
                emu.getMemory().write8(seg.vaddr + i, 0);
        }
        uint32_t entry = ElfLoader::getEntryPoint(buffer);
        emu.getCPU().setPC(entry);
    }
    emu.getCPU().setReg(2, 512 * 1024 * 1024);

    // Warm up: let the game run a few frames with no key
    run_frames(emu, -1, 2);

    // Capture initial state (no key pressed)
    run_frames(emu, 0, FRAMES_PER_KEY);
    dump_framebuffer_hex(emu.getMemory());

    // Press 'w' (move up) and let it settle
    run_frames(emu, 'w', FRAMES_PER_KEY);
    // Then clear key and let game settle on the new position
    run_frames(emu, 0, FRAMES_PER_KEY);
    dump_framebuffer_hex(emu.getMemory());

    // Press 's' (move down) and let it settle
    run_frames(emu, 's', FRAMES_PER_KEY);
    // Then clear key and let game settle on the new position
    run_frames(emu, 0, FRAMES_PER_KEY);
    dump_framebuffer_hex(emu.getMemory());

    return 0;
}
