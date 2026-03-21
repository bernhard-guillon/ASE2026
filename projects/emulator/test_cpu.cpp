#include <gtest/gtest.h>
#include "CPU.h"

class CPUTest : public ::testing::Test {
protected:
    CPU cpu;
};

// Register initialization
TEST_F(CPUTest, RegistersInitiallyZero) {
    for (uint8_t i = 0; i < CPU::NUM_REGISTERS; ++i) {
        EXPECT_EQ(cpu.getReg(i), 0) << "Register x" << static_cast<int>(i);
    }
}

// x0 hardwired to zero
TEST_F(CPUTest, X0AlwaysZero) {
    EXPECT_EQ(cpu.getReg(0), 0);
    
    // Attempt to write to x0
    cpu.setReg(0, 0x12345678);
    
    // x0 should still be zero
    EXPECT_EQ(cpu.getReg(0), 0);
}

TEST_F(CPUTest, X0RemainsZeroAfterMultipleWrites) {
    cpu.setReg(0, 0xFFFFFFFF);
    cpu.setReg(0, 0xAAAAAAAA);
    cpu.setReg(0, 0x55555555);
    
    EXPECT_EQ(cpu.getReg(0), 0);
}

// Basic register access
TEST_F(CPUTest, SetAndGetRegister) {
    cpu.setReg(1, 0x12345678);
    EXPECT_EQ(cpu.getReg(1), 0x12345678);
    
    cpu.setReg(15, 0xDEADBEEF);
    EXPECT_EQ(cpu.getReg(15), 0xDEADBEEF);
    
    cpu.setReg(31, 0xCAFEBABE);
    EXPECT_EQ(cpu.getReg(31), 0xCAFEBABE);
}

TEST_F(CPUTest, RegistersIndependent) {
    cpu.setReg(1, 0x11111111);
    cpu.setReg(2, 0x22222222);
    cpu.setReg(3, 0x33333333);
    
    EXPECT_EQ(cpu.getReg(1), 0x11111111);
    EXPECT_EQ(cpu.getReg(2), 0x22222222);
    EXPECT_EQ(cpu.getReg(3), 0x33333333);
}

TEST_F(CPUTest, OverwriteRegister) {
    cpu.setReg(5, 0xAAAAAAAA);
    EXPECT_EQ(cpu.getReg(5), 0xAAAAAAAA);
    
    cpu.setReg(5, 0x55555555);
    EXPECT_EQ(cpu.getReg(5), 0x55555555);
}

TEST_F(CPUTest, AllRegistersAccessible) {
    // Write unique value to each register (except x0)
    for (uint8_t i = 1; i < CPU::NUM_REGISTERS; ++i) {
        uint32_t value = 0x1000 + i;
        cpu.setReg(i, value);
    }
    
    // Verify each register
    for (uint8_t i = 1; i < CPU::NUM_REGISTERS; ++i) {
        uint32_t expected = 0x1000 + i;
        EXPECT_EQ(cpu.getReg(i), expected) << "Register x" << static_cast<int>(i);
    }
}

// Bounds checking
TEST_F(CPUTest, GetInvalidRegisterThrows) {
    EXPECT_THROW(cpu.getReg(32), std::out_of_range);
    EXPECT_THROW(cpu.getReg(33), std::out_of_range);
    EXPECT_THROW(cpu.getReg(255), std::out_of_range);
}

TEST_F(CPUTest, SetInvalidRegisterThrows) {
    EXPECT_THROW(cpu.setReg(32, 0x12345678), std::out_of_range);
    EXPECT_THROW(cpu.setReg(33, 0x12345678), std::out_of_range);
    EXPECT_THROW(cpu.setReg(255, 0x12345678), std::out_of_range);
}

// Program counter
TEST_F(CPUTest, PCInitiallyZero) {
    EXPECT_EQ(cpu.getPC(), 0);
}

TEST_F(CPUTest, SetAndGetPC) {
    cpu.setPC(0x1000);
    EXPECT_EQ(cpu.getPC(), 0x1000);
    
    cpu.setPC(0x80000000);
    EXPECT_EQ(cpu.getPC(), 0x80000000);
}

TEST_F(CPUTest, IncrementPC) {
    cpu.setPC(0x1000);
    
    cpu.incrementPC();
    EXPECT_EQ(cpu.getPC(), 0x1004);
    
    cpu.incrementPC();
    EXPECT_EQ(cpu.getPC(), 0x1008);
    
    cpu.incrementPC();
    EXPECT_EQ(cpu.getPC(), 0x100C);
}

TEST_F(CPUTest, IncrementPCFromZero) {
    EXPECT_EQ(cpu.getPC(), 0);
    
    cpu.incrementPC();
    EXPECT_EQ(cpu.getPC(), 4);
}

TEST_F(CPUTest, PCWrapAround) {
    cpu.setPC(0xFFFFFFFC);
    cpu.incrementPC();
    
    // Should wrap around (32-bit overflow)
    EXPECT_EQ(cpu.getPC(), 0);
}

// Reset
TEST_F(CPUTest, ResetClearsRegisters) {
    // Write to multiple registers
    cpu.setReg(1, 0x12345678);
    cpu.setReg(10, 0xDEADBEEF);
    cpu.setReg(31, 0xCAFEBABE);
    
    cpu.reset();
    
    // All registers should be zero
    for (uint8_t i = 0; i < CPU::NUM_REGISTERS; ++i) {
        EXPECT_EQ(cpu.getReg(i), 0) << "Register x" << static_cast<int>(i);
    }
}

TEST_F(CPUTest, ResetClearsPC) {
    cpu.setPC(0x12345678);
    
    cpu.reset();
    
    EXPECT_EQ(cpu.getPC(), 0);
}

TEST_F(CPUTest, ResetPreservesX0Invariant) {
    cpu.setReg(0, 0xFFFFFFFF);  // This should be ignored
    
    cpu.reset();
    
    EXPECT_EQ(cpu.getReg(0), 0);
}

// Edge cases
TEST_F(CPUTest, MaxRegisterValues) {
    cpu.setReg(1, 0xFFFFFFFF);
    EXPECT_EQ(cpu.getReg(1), 0xFFFFFFFF);
    
    cpu.setReg(2, 0x00000000);
    EXPECT_EQ(cpu.getReg(2), 0x00000000);
}

TEST_F(CPUTest, AllBitsPattern) {
    // Test various bit patterns
    uint32_t patterns[] = {
        0x00000000,
        0xFFFFFFFF,
        0xAAAAAAAA,
        0x55555555,
        0x80000000,
        0x7FFFFFFF,
        0x12345678,
        0xDEADBEEF
    };
    
    for (uint32_t pattern : patterns) {
        cpu.setReg(10, pattern);
        EXPECT_EQ(cpu.getReg(10), pattern);
    }
}
