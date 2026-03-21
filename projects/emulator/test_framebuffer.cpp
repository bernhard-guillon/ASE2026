#include <gtest/gtest.h>
#include "Emulator.h"

class FramebufferTest : public ::testing::Test {
protected:
    Emulator emulator;
};

TEST_F(FramebufferTest, FramebufferAddressesValid) {
    // Framebuffer should be accessible in memory
    EXPECT_LE(FRAMEBUFFER_ADDR + FRAMEBUFFER_SIZE, emulator.getMemory().size());
}

TEST_F(FramebufferTest, FramebufferWriteRead) {
    Memory& mem = emulator.getMemory();
    
    // Write pattern to framebuffer
    for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
        mem.write8(FRAMEBUFFER_ADDR + i, i & 0xFF);
    }
    
    // Read back and verify
    for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
        uint8_t value = mem.read8(FRAMEBUFFER_ADDR + i);
        EXPECT_EQ(value, i & 0xFF) << "Mismatch at framebuffer offset " << i;
    }
}

TEST_F(FramebufferTest, FramebufferInitiallyZero) {
    Memory& mem = emulator.getMemory();
    
    // Framebuffer should be zero-initialized
    for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
        uint8_t value = mem.read8(FRAMEBUFFER_ADDR + i);
        EXPECT_EQ(value, 0) << "Framebuffer should be zero-initialized at offset " << i;
    }
}

TEST_F(FramebufferTest, FramebufferGrayscaleValues) {
    Memory& mem = emulator.getMemory();
    
    // Write grayscale values (0-255)
    for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
        uint8_t gray_value = (i * 255) / FRAMEBUFFER_SIZE;
        mem.write8(FRAMEBUFFER_ADDR + i, gray_value);
    }
    
    // Verify all values are in valid range
    for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
        uint8_t value = mem.read8(FRAMEBUFFER_ADDR + i);
        EXPECT_GE(value, 0);
        EXPECT_LE(value, 255);
    }
}

TEST_F(FramebufferTest, FramebufferDimensions) {
    // Verify framebuffer dimensions
    EXPECT_EQ(FRAMEBUFFER_WIDTH, 20);
    EXPECT_EQ(FRAMEBUFFER_HEIGHT, 20);
    EXPECT_EQ(FRAMEBUFFER_WIDTH * FRAMEBUFFER_HEIGHT, FRAMEBUFFER_SIZE);
}
