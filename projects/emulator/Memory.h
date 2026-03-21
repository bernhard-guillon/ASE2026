#ifndef MEMORY_H
#define MEMORY_H

#include <cstdint>
#include <vector>
#include <stdexcept>

class Memory {
public:
    explicit Memory(size_t size);
    
    // 8-bit access
    uint8_t read8(uint32_t address) const;
    void write8(uint32_t address, uint8_t value);
    
    // 32-bit access (little-endian)
    uint32_t read32(uint32_t address) const;
    void write32(uint32_t address, uint32_t value);
    
    // Utility
    size_t size() const { return memory_.size(); }
    void reset();
    
private:
    std::vector<uint8_t> memory_;
    
    void checkBounds(uint32_t address, size_t access_size) const;
};

#endif // MEMORY_H
