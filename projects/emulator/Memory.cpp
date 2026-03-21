#include "Memory.h"

Memory::Memory(size_t size) : memory_(size, 0) {
    if (size == 0) {
        throw std::invalid_argument("Memory size must be greater than 0");
    }
}

void Memory::checkBounds(uint32_t address, size_t access_size) const {
    if (address + access_size > memory_.size()) {
        throw std::out_of_range("Memory access out of bounds");
    }
}

uint8_t Memory::read8(uint32_t address) const {
    checkBounds(address, 1);
    return memory_[address];
}

void Memory::write8(uint32_t address, uint8_t value) {
    checkBounds(address, 1);
    memory_[address] = value;
}

uint32_t Memory::read32(uint32_t address) const {
    checkBounds(address, 4);
    
    // Little-endian: least significant byte first
    uint32_t value = 0;
    value |= static_cast<uint32_t>(memory_[address + 0]) << 0;
    value |= static_cast<uint32_t>(memory_[address + 1]) << 8;
    value |= static_cast<uint32_t>(memory_[address + 2]) << 16;
    value |= static_cast<uint32_t>(memory_[address + 3]) << 24;
    
    return value;
}

void Memory::write32(uint32_t address, uint32_t value) {
    checkBounds(address, 4);
    
    // Little-endian: least significant byte first
    memory_[address + 0] = static_cast<uint8_t>((value >> 0) & 0xFF);
    memory_[address + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    memory_[address + 2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    memory_[address + 3] = static_cast<uint8_t>((value >> 24) & 0xFF);
}

void Memory::reset() {
    std::fill(memory_.begin(), memory_.end(), 0);
}
