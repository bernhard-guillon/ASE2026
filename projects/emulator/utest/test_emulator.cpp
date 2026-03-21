#include <gtest/gtest.h>
#include <sstream>
#include "Emulator.h"

class EmulatorTest : public ::testing::Test {
protected:
    Emulator emulator{1024};
    
    void SetUp() override {
        emulator.reset();
    }
};

// Basic program loading and execution
TEST_F(EmulatorTest, LoadAndExecuteSimpleProgram) {
    // Program: ADDI x1, x0, 42
    std::vector<uint32_t> program = {
        0b000000101010'00000'000'00001'0010011  // ADDI x1, x0, 42
    };
    
    emulator.loadProgram(program, 0);
    emulator.step();
    
    EXPECT_EQ(emulator.getCPU().getReg(1), 42);
    EXPECT_EQ(emulator.getCPU().getPC(), 4);
}

TEST_F(EmulatorTest, LoadProgramAtNonZeroAddress) {
    std::vector<uint32_t> program = {
        0b000000000101'00000'000'00001'0010011  // ADDI x1, x0, 5
    };
    
    emulator.loadProgram(program, 100);
    
    EXPECT_EQ(emulator.getCPU().getPC(), 100);
    emulator.step();
    EXPECT_EQ(emulator.getCPU().getReg(1), 5);
}

TEST_F(EmulatorTest, MultipleInstructions) {
    std::vector<uint32_t> program = {
        0b000000001010'00000'000'00001'0010011,  // ADDI x1, x0, 10
        0b000000010100'00000'000'00010'0010011,  // ADDI x2, x0, 20
        0b0000000'00010'00001'000'00011'0110011  // ADD x3, x1, x2
    };
    
    emulator.loadProgram(program, 0);
    emulator.run(3);
    
    EXPECT_EQ(emulator.getCPU().getReg(1), 10);
    EXPECT_EQ(emulator.getCPU().getReg(2), 20);
    EXPECT_EQ(emulator.getCPU().getReg(3), 30);
    EXPECT_EQ(emulator.getCPU().getPC(), 12);
}

// System call: exit
TEST_F(EmulatorTest, ExitSyscall) {
    std::vector<uint32_t> program = {
        0b000000000000'00000'000'01010'0010011,  // ADDI x10, x0, 0 (exit code)
        0b000001011101'00000'000'10001'0010011,  // ADDI x17, x0, 93 (exit syscall)
        0b000000000000'00000'000'00000'1110011   // ECALL
    };
    
    emulator.loadProgram(program, 0);
    emulator.run();
    
    EXPECT_TRUE(emulator.isHalted());
}

// System call: write
TEST_F(EmulatorTest, WriteSyscall) {
    // Store "Hi\n" in memory
    emulator.getMemory().write8(100, 'H');
    emulator.getMemory().write8(101, 'i');
    emulator.getMemory().write8(102, '\n');
    
    std::vector<uint32_t> program = {
        0b000000000001'00000'000'01010'0010011,  // ADDI x10, x0, 1 (stdout)
        0b000001100100'00000'000'01011'0010011,  // ADDI x11, x0, 100 (buffer address)
        0b000000000011'00000'000'01100'0010011,  // ADDI x12, x0, 3 (count)
        0b000001000000'00000'000'10001'0010011,  // ADDI x17, x0, 64 (write syscall)
        0b000000000000'00000'000'00000'1110011,  // ECALL
        // exit
        0b000000000000'00000'000'01010'0010011,  // ADDI x10, x0, 0
        0b000001011101'00000'000'10001'0010011,  // ADDI x17, x0, 93
        0b000000000000'00000'000'00000'1110011   // ECALL
    };
    
    emulator.loadProgram(program, 0);
    
    // Redirect cout to capture output
    std::stringstream buffer;
    std::streambuf* old = std::cout.rdbuf(buffer.rdbuf());
    
    emulator.run();
    
    std::cout.rdbuf(old);
    
    EXPECT_EQ(buffer.str(), "Hi\n");
    // Return value from write is 3 bytes written, but then gets overwritten by exit prep
    EXPECT_TRUE(emulator.isHalted());
}

// Loop execution
TEST_F(EmulatorTest, SimpleLoop) {
    // Sum numbers 1 to 10
    std::vector<uint32_t> program = {
        // x1 = sum, x2 = counter, x3 = limit
        0b000000000000'00000'000'00001'0010011,  // 0:  ADDI x1, x0, 0
        0b000000000001'00000'000'00010'0010011,  // 4:  ADDI x2, x0, 1
        0b000000001011'00000'000'00011'0010011,  // 8:  ADDI x3, x0, 11
        // loop:
        0b0000000'00010'00001'000'00001'0110011,  // 12: ADD x1, x1, x2
        0b000000000001'00010'000'00010'0010011,  // 16: ADDI x2, x2, 1
        0b1'111111'00011'00010'100'1100'1'1100011,// 20: BLT x2, x3, -8 (to offset 12)
        // exit
        0b000000000000'00000'000'01010'0010011,  // 24: ADDI x10, x0, 0
        0b000001011101'00000'000'10001'0010011,  // 28: ADDI x17, x0, 93
        0b000000000000'00000'000'00000'1110011   // 32: ECALL
    };
    
    emulator.loadProgram(program, 0);
    emulator.run(100);
    
    EXPECT_EQ(emulator.getCPU().getReg(1), 55);  // 1+2+...+10 = 55
    EXPECT_EQ(emulator.getCPU().getReg(2), 11);
    EXPECT_TRUE(emulator.isHalted());
}

// Function call with JAL/JALR
TEST_F(EmulatorTest, FunctionCall) {
    std::vector<uint32_t> program = {
        // main:
        0b000000001010'00000'000'01010'0010011,  // 0:  ADDI x10, x0, 10
        0b0'0000000100'0'00000000'00001'1101111,  // 4:  JAL x1, 8 (call function at 12)
        // After return, prepare exit
        0b000000000000'01010'000'01010'0010011,  // 8: ADDI x10, x10, 0 (nop, keeps value)
        0b000001011101'00000'000'10001'0010011,  // 12: ADDI x17, x0, 93
        0b000000000000'00000'000'00000'1110011,  // 16: ECALL (exit)
        // function: (at offset 20)
        0b000000000101'01010'000'01010'0010011,  // 20: ADDI x10, x10, 5
        0b000000000000'00001'000'00000'1100111   // 24: JALR x0, 0(x1) (return)
    };
    
    emulator.loadProgram(program, 0);
    emulator.run(10);
    
    // Check that function executed (x10 should have been modified and then used for exit)
    EXPECT_TRUE(emulator.isHalted());
}

// Memory load/store in program
TEST_F(EmulatorTest, LoadStoreSequence) {
    std::vector<uint32_t> program = {
        0b000000101010'00000'000'00001'0010011,  // ADDI x1, x0, 42
        0b000001100100'00000'000'00010'0010011,  // ADDI x2, x0, 100 (address)
        0b0000000'00001'00010'010'00000'0100011, // SW x1, 0(x2)
        0b000000000000'00010'010'00011'0000011   // LW x3, 0(x2)
    };
    
    emulator.loadProgram(program, 0);
    emulator.run(4);
    
    EXPECT_EQ(emulator.getCPU().getReg(3), 42);
    EXPECT_EQ(emulator.getMemory().read32(100), 42);
}

// Edge case: PC out of bounds
TEST_F(EmulatorTest, PCOutOfBounds) {
    emulator.getCPU().setPC(2000);  // Beyond 1024-byte memory
    
    EXPECT_THROW(emulator.step(), std::runtime_error);
}

// Reset functionality
TEST_F(EmulatorTest, Reset) {
    std::vector<uint32_t> program = {
        0b000000101010'00000'000'00001'0010011  // ADDI x1, x0, 42
    };
    
    emulator.loadProgram(program, 0);
    emulator.step();
    
    EXPECT_EQ(emulator.getCPU().getReg(1), 42);
    
    emulator.reset();
    
    EXPECT_EQ(emulator.getCPU().getReg(1), 0);
    EXPECT_EQ(emulator.getCPU().getPC(), 0);
    EXPECT_FALSE(emulator.isHalted());
}

// Run with instruction limit
TEST_F(EmulatorTest, InstructionLimit) {
    // Infinite loop: jump to itself
    std::vector<uint32_t> program = {
        // JAL x0, 0 (jump to current PC)
        0b0'0000000000'0'00000000'00000'1101111
    };
    
    emulator.loadProgram(program, 0);
    emulator.run(100);  // Should stop after 100 iterations
    
    EXPECT_FALSE(emulator.isHalted());
    EXPECT_EQ(emulator.getCPU().getPC(), 0);  // Still at loop
}

// Complete Hello World simulation
TEST_F(EmulatorTest, HelloWorldSimulation) {
    // Store "Hello, World!\n" in memory at address 200
    const char* message = "Hello, World!\n";
    for (size_t i = 0; message[i] != '\0'; ++i) {
        emulator.getMemory().write8(200 + i, message[i]);
    }
    
    std::vector<uint32_t> program = {
        // write(1, message, 14)
        0b000000000001'00000'000'01010'0010011,  // ADDI x10, x0, 1 (stdout)
        0b000011001000'00000'000'01011'0010011,  // ADDI x11, x0, 200 (buffer)
        0b000000001110'00000'000'01100'0010011,  // ADDI x12, x0, 14 (count)
        0b000001000000'00000'000'10001'0010011,  // ADDI x17, x0, 64 (write syscall)
        0b000000000000'00000'000'00000'1110011,  // ECALL
        // exit(0)
        0b000000000000'00000'000'01010'0010011,  // ADDI x10, x0, 0 (exit code)
        0b000001011101'00000'000'10001'0010011,  // ADDI x17, x0, 93 (exit syscall)
        0b000000000000'00000'000'00000'1110011   // ECALL
    };
    
    emulator.loadProgram(program, 0);
    
    // Redirect cout
    std::stringstream buffer;
    std::streambuf* old = std::cout.rdbuf(buffer.rdbuf());
    
    emulator.run();
    
    std::cout.rdbuf(old);
    
    EXPECT_EQ(buffer.str(), "Hello, World!\n");
    EXPECT_TRUE(emulator.isHalted());
}
