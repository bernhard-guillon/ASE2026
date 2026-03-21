#include <gtest/gtest.h>
#include "Memory.h"

class MemoryTest : public ::testing::Test {
protected:
    static constexpr size_t MEM_SIZE = 1024;
    Memory mem{MEM_SIZE};
};

// Basic 8-bit operations
TEST_F(MemoryTest, Read8InitiallyZero) {
    EXPECT_EQ(mem.read8(0), 0);
    EXPECT_EQ(mem.read8(100), 0);
    EXPECT_EQ(mem.read8(MEM_SIZE - 1), 0);
}

TEST_F(MemoryTest, Write8Read8) {
    mem.write8(0, 0x42);
    EXPECT_EQ(mem.read8(0), 0x42);
    
    mem.write8(100, 0xFF);
    EXPECT_EQ(mem.read8(100), 0xFF);
    
    // Verify other locations unchanged
    EXPECT_EQ(mem.read8(1), 0);
    EXPECT_EQ(mem.read8(99), 0);
}

TEST_F(MemoryTest, Write8Boundary) {
    mem.write8(MEM_SIZE - 1, 0xAB);
    EXPECT_EQ(mem.read8(MEM_SIZE - 1), 0xAB);
}

// Basic 32-bit operations
TEST_F(MemoryTest, Read32InitiallyZero) {
    EXPECT_EQ(mem.read32(0), 0);
    EXPECT_EQ(mem.read32(100), 0);
}

TEST_F(MemoryTest, Write32Read32) {
    mem.write32(0, 0x12345678);
    EXPECT_EQ(mem.read32(0), 0x12345678);
    
    mem.write32(100, 0xDEADBEEF);
    EXPECT_EQ(mem.read32(100), 0xDEADBEEF);
}

TEST_F(MemoryTest, Write32LittleEndian) {
    mem.write32(0, 0x12345678);
    
    // Verify little-endian byte order
    EXPECT_EQ(mem.read8(0), 0x78);  // LSB
    EXPECT_EQ(mem.read8(1), 0x56);
    EXPECT_EQ(mem.read8(2), 0x34);
    EXPECT_EQ(mem.read8(3), 0x12);  // MSB
}

TEST_F(MemoryTest, Write8Read32) {
    // Write individual bytes and read as 32-bit word
    mem.write8(0, 0xAA);
    mem.write8(1, 0xBB);
    mem.write8(2, 0xCC);
    mem.write8(3, 0xDD);
    
    EXPECT_EQ(mem.read32(0), 0xDDCCBBAA);  // Little-endian
}

TEST_F(MemoryTest, Write32Read8) {
    mem.write32(0, 0x12345678);
    
    EXPECT_EQ(mem.read8(0), 0x78);
    EXPECT_EQ(mem.read8(1), 0x56);
    EXPECT_EQ(mem.read8(2), 0x34);
    EXPECT_EQ(mem.read8(3), 0x12);
}

// Bounds checking
TEST_F(MemoryTest, Read8OutOfBounds) {
    EXPECT_THROW(mem.read8(MEM_SIZE), std::out_of_range);
    EXPECT_THROW(mem.read8(MEM_SIZE + 100), std::out_of_range);
}

TEST_F(MemoryTest, Write8OutOfBounds) {
    EXPECT_THROW(mem.write8(MEM_SIZE, 0x42), std::out_of_range);
    EXPECT_THROW(mem.write8(MEM_SIZE + 100, 0x42), std::out_of_range);
}

TEST_F(MemoryTest, Read32OutOfBounds) {
    // These should fail because we need 4 bytes
    EXPECT_THROW(mem.read32(MEM_SIZE - 3), std::out_of_range);
    EXPECT_THROW(mem.read32(MEM_SIZE - 2), std::out_of_range);
    EXPECT_THROW(mem.read32(MEM_SIZE - 1), std::out_of_range);
    EXPECT_THROW(mem.read32(MEM_SIZE), std::out_of_range);
}

TEST_F(MemoryTest, Write32OutOfBounds) {
    EXPECT_THROW(mem.write32(MEM_SIZE - 3, 0x12345678), std::out_of_range);
    EXPECT_THROW(mem.write32(MEM_SIZE, 0x12345678), std::out_of_range);
}

TEST_F(MemoryTest, Read32AtBoundary) {
    // This should work: exactly 4 bytes at end
    mem.write32(MEM_SIZE - 4, 0xCAFEBABE);
    EXPECT_EQ(mem.read32(MEM_SIZE - 4), 0xCAFEBABE);
}

// Reset functionality
TEST_F(MemoryTest, Reset) {
    mem.write32(0, 0x12345678);
    mem.write8(100, 0xFF);
    
    mem.reset();
    
    EXPECT_EQ(mem.read32(0), 0);
    EXPECT_EQ(mem.read8(100), 0);
}

// Size validation
TEST_F(MemoryTest, ConstructorRejectsZeroSize) {
    EXPECT_THROW(Memory(0), std::invalid_argument);
}

TEST_F(MemoryTest, SizeMethod) {
    Memory small(64);
    EXPECT_EQ(small.size(), 64);
    
    Memory large(8192);
    EXPECT_EQ(large.size(), 8192);
}

// Multiple non-overlapping writes
TEST_F(MemoryTest, MultipleWrites) {
    mem.write32(0, 0x11111111);
    mem.write32(4, 0x22222222);
    mem.write32(8, 0x33333333);
    
    EXPECT_EQ(mem.read32(0), 0x11111111);
    EXPECT_EQ(mem.read32(4), 0x22222222);
    EXPECT_EQ(mem.read32(8), 0x33333333);
}

// Overlapping writes
TEST_F(MemoryTest, OverlappingWrites) {
    mem.write32(0, 0xFFFFFFFF);
    mem.write8(1, 0x00);  // Modify second byte
    
    EXPECT_EQ(mem.read32(0), 0xFFFF00FF);
}
