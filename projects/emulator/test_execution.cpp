#include <gtest/gtest.h>
#include "CPU.h"
#include "Memory.h"
#include "Instruction.h"

class ExecutionTest : public ::testing::Test {
protected:
    CPU cpu;
    Memory memory{1024};
    
    void SetUp() override {
        cpu.reset();
        memory.reset();
    }
};

// R-Type ALU operations

TEST_F(ExecutionTest, ADD) {
    cpu.setReg(1, 10);
    cpu.setReg(2, 20);
    
    // ADD x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'000'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 30);
    EXPECT_EQ(cpu.getPC(), 4);
}

TEST_F(ExecutionTest, SUB) {
    cpu.setReg(1, 50);
    cpu.setReg(2, 20);
    
    // SUB x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0100000'00010'00001'000'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 30);
}

TEST_F(ExecutionTest, AND) {
    cpu.setReg(1, 0b11110000);
    cpu.setReg(2, 0b11001100);
    
    // AND x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'111'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b11000000);
}

TEST_F(ExecutionTest, OR) {
    cpu.setReg(1, 0b11110000);
    cpu.setReg(2, 0b11001100);
    
    // OR x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'110'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b11111100);
}

TEST_F(ExecutionTest, XOR) {
    cpu.setReg(1, 0b11110000);
    cpu.setReg(2, 0b11001100);
    
    // XOR x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'100'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b00111100);
}

TEST_F(ExecutionTest, SLL) {
    cpu.setReg(1, 0b00000001);
    cpu.setReg(2, 4);
    
    // SLL x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'001'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b00010000);
}

TEST_F(ExecutionTest, SRL) {
    cpu.setReg(1, 0b10000000);
    cpu.setReg(2, 4);
    
    // SRL x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'101'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b00001000);
}

TEST_F(ExecutionTest, SRA_Positive) {
    cpu.setReg(1, 0b01000000);
    cpu.setReg(2, 2);
    
    // SRA x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0100000'00010'00001'101'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0b00010000);
}

TEST_F(ExecutionTest, SRA_Negative) {
    cpu.setReg(1, 0x80000000);  // Most significant bit set (negative)
    cpu.setReg(2, 4);
    
    // SRA x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0100000'00010'00001'101'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0xF8000000);  // Sign-extended
}

TEST_F(ExecutionTest, SLT_True) {
    cpu.setReg(1, static_cast<uint32_t>(-5));  // -5 as signed
    cpu.setReg(2, 10);
    
    // SLT x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'010'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 1);  // -5 < 10
}

TEST_F(ExecutionTest, SLT_False) {
    cpu.setReg(1, 20);
    cpu.setReg(2, 10);
    
    // SLT x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'010'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0);  // 20 >= 10
}

TEST_F(ExecutionTest, SLTU_True) {
    cpu.setReg(1, 5);
    cpu.setReg(2, 10);
    
    // SLTU x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'011'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 1);
}

TEST_F(ExecutionTest, SLTU_False) {
    cpu.setReg(1, 0xFFFFFFFF);  // Large unsigned value
    cpu.setReg(2, 10);
    
    // SLTU x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'011'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0);  // 0xFFFFFFFF > 10 (unsigned)
}

// I-Type immediate operations

TEST_F(ExecutionTest, ADDI) {
    cpu.setReg(1, 10);
    
    // ADDI x2, x1, 42
    Instruction instr = InstructionDecoder::decode(0b000000101010'00001'000'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 52);
    EXPECT_EQ(cpu.getPC(), 4);
}

TEST_F(ExecutionTest, ADDI_Negative) {
    cpu.setReg(1, 100);
    
    // ADDI x2, x1, -10 (imm = 0xFFF6)
    Instruction instr = InstructionDecoder::decode(0b111111110110'00001'000'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 90);
}

TEST_F(ExecutionTest, ANDI) {
    cpu.setReg(1, 0xFF);
    
    // ANDI x2, x1, 0x0F
    Instruction instr = InstructionDecoder::decode(0b000000001111'00001'111'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0x0F);
}

TEST_F(ExecutionTest, ORI) {
    cpu.setReg(1, 0xF0);
    
    // ORI x2, x1, 0x0F
    Instruction instr = InstructionDecoder::decode(0b000000001111'00001'110'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xFF);
}

TEST_F(ExecutionTest, XORI) {
    cpu.setReg(1, 0b11110000);
    
    // XORI x2, x1, 0b11001100
    Instruction instr = InstructionDecoder::decode(0b000011001100'00001'100'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0b00111100);
}

TEST_F(ExecutionTest, SLLI) {
    cpu.setReg(1, 1);
    
    // SLLI x2, x1, 4
    Instruction instr = InstructionDecoder::decode(0b0000000'00100'00001'001'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 16);
}

TEST_F(ExecutionTest, SRLI) {
    cpu.setReg(1, 0x80);
    
    // SRLI x2, x1, 4
    Instruction instr = InstructionDecoder::decode(0b0000000'00100'00001'101'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0x08);
}

TEST_F(ExecutionTest, SRAI_Positive) {
    cpu.setReg(1, 0x40);
    
    // SRAI x2, x1, 2
    Instruction instr = InstructionDecoder::decode(0b0100000'00010'00001'101'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0x10);
}

TEST_F(ExecutionTest, SRAI_Negative) {
    cpu.setReg(1, 0x80000000);
    
    // SRAI x2, x1, 4
    Instruction instr = InstructionDecoder::decode(0b0100000'00100'00001'101'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xF8000000);  // Sign-extended
}

TEST_F(ExecutionTest, SLTI_True) {
    cpu.setReg(1, static_cast<uint32_t>(-10));
    
    // SLTI x2, x1, 5
    Instruction instr = InstructionDecoder::decode(0b000000000101'00001'010'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 1);  // -10 < 5
}

TEST_F(ExecutionTest, SLTI_False) {
    cpu.setReg(1, 10);
    
    // SLTI x2, x1, 5
    Instruction instr = InstructionDecoder::decode(0b000000000101'00001'010'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0);  // 10 >= 5
}

TEST_F(ExecutionTest, SLTIU) {
    cpu.setReg(1, 5);
    
    // SLTIU x2, x1, 10
    Instruction instr = InstructionDecoder::decode(0b000000001010'00001'011'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 1);
}

// Edge cases

TEST_F(ExecutionTest, ShiftBy31) {
    cpu.setReg(1, 1);
    cpu.setReg(2, 31);
    
    // SLL x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'001'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0x80000000);
}

TEST_F(ExecutionTest, ShiftByMoreThan31) {
    cpu.setReg(1, 1);
    cpu.setReg(2, 35);  // Should use only lower 5 bits (35 & 0x1F = 3)
    
    // SLL x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'001'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 8);  // 1 << 3
}

TEST_F(ExecutionTest, X0DestinationIgnored) {
    cpu.setReg(1, 10);
    cpu.setReg(2, 20);
    
    // ADD x0, x1, x2 (result should be discarded)
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'000'00000'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(0), 0);  // x0 remains zero
}

TEST_F(ExecutionTest, X0SourceValue) {
    cpu.setReg(2, 42);
    
    // ADD x3, x0, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00000'000'00011'0110011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 42);  // 0 + 42
}

TEST_F(ExecutionTest, MultipleInstructions) {
    cpu.setReg(1, 5);
    
    // ADDI x2, x1, 10
    Instruction instr1 = InstructionDecoder::decode(0b000000001010'00001'000'00010'0010011);
    cpu.execute(instr1, memory);
    EXPECT_EQ(cpu.getReg(2), 15);
    EXPECT_EQ(cpu.getPC(), 4);
    
    // ADD x3, x1, x2
    Instruction instr2 = InstructionDecoder::decode(0b0000000'00010'00001'000'00011'0110011);
    cpu.execute(instr2, memory);
    EXPECT_EQ(cpu.getReg(3), 20);
    EXPECT_EQ(cpu.getPC(), 8);
}

// Load/Store operations

TEST_F(ExecutionTest, LW_LoadWord) {
    memory.write32(100, 0x12345678);
    cpu.setReg(1, 100);
    
    // LW x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'010'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0x12345678);
    EXPECT_EQ(cpu.getPC(), 4);
}

TEST_F(ExecutionTest, LW_WithOffset) {
    memory.write32(108, 0xDEADBEEF);
    cpu.setReg(1, 100);
    
    // LW x2, 8(x1)
    Instruction instr = InstructionDecoder::decode(0b000000001000'00001'010'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xDEADBEEF);
}

TEST_F(ExecutionTest, LB_SignExtend) {
    memory.write8(100, 0xFF);  // -1 as signed byte
    cpu.setReg(1, 100);
    
    // LB x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'000'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xFFFFFFFF);  // Sign-extended to -1
}

TEST_F(ExecutionTest, LBU_ZeroExtend) {
    memory.write8(100, 0xFF);
    cpu.setReg(1, 100);
    
    // LBU x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'100'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xFF);  // Zero-extended
}

TEST_F(ExecutionTest, LH_SignExtend) {
    memory.write8(100, 0xFF);
    memory.write8(101, 0xFF);  // 0xFFFF = -1 as signed halfword
    cpu.setReg(1, 100);
    
    // LH x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'001'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xFFFFFFFF);  // Sign-extended
}

TEST_F(ExecutionTest, LHU_ZeroExtend) {
    memory.write8(100, 0xFF);
    memory.write8(101, 0xFF);
    cpu.setReg(1, 100);
    
    // LHU x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'101'00010'0000011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 0xFFFF);  // Zero-extended
}

TEST_F(ExecutionTest, SW_StoreWord) {
    cpu.setReg(1, 100);
    cpu.setReg(2, 0x12345678);
    
    // SW x2, 0(x1)
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'010'00000'0100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(memory.read32(100), 0x12345678);
    EXPECT_EQ(cpu.getPC(), 4);
}

TEST_F(ExecutionTest, SW_WithOffset) {
    cpu.setReg(1, 100);
    cpu.setReg(2, 0xDEADBEEF);
    
    // SW x2, 12(x1)  imm[11:5]=0, imm[4:0]=12
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'010'01100'0100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(memory.read32(112), 0xDEADBEEF);
}

TEST_F(ExecutionTest, SB_StoreByte) {
    cpu.setReg(1, 100);
    cpu.setReg(2, 0x12345678);
    
    // SB x2, 0(x1) - should store only 0x78
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'000'00000'0100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(memory.read8(100), 0x78);
}

TEST_F(ExecutionTest, SH_StoreHalfword) {
    cpu.setReg(1, 100);
    cpu.setReg(2, 0x12345678);
    
    // SH x2, 0(x1) - should store 0x5678
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'001'00000'0100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(memory.read8(100), 0x78);
    EXPECT_EQ(memory.read8(101), 0x56);
}

// Branch operations

TEST_F(ExecutionTest, BEQ_Taken) {
    cpu.setReg(1, 42);
    cpu.setReg(2, 42);
    cpu.setPC(100);
    
    // BEQ x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'000'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);  // 100 + 8
}

TEST_F(ExecutionTest, BEQ_NotTaken) {
    cpu.setReg(1, 42);
    cpu.setReg(2, 43);
    cpu.setPC(100);
    
    // BEQ x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'000'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);  // 100 + 4 (not taken)
}

TEST_F(ExecutionTest, BNE_Taken) {
    cpu.setReg(1, 42);
    cpu.setReg(2, 43);
    cpu.setPC(100);
    
    // BNE x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'001'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);
}

TEST_F(ExecutionTest, BNE_NotTaken) {
    cpu.setReg(1, 42);
    cpu.setReg(2, 42);
    cpu.setPC(100);
    
    // BNE x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'001'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);
}

TEST_F(ExecutionTest, BLT_Taken_Negative) {
    cpu.setReg(1, static_cast<uint32_t>(-5));
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BLT x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'100'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);  // -5 < 10
}

TEST_F(ExecutionTest, BLT_NotTaken) {
    cpu.setReg(1, 20);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BLT x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'100'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);  // 20 >= 10
}

TEST_F(ExecutionTest, BGE_Taken) {
    cpu.setReg(1, 20);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BGE x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'101'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);
}

TEST_F(ExecutionTest, BGE_NotTaken) {
    cpu.setReg(1, 5);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BGE x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'101'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);
}

TEST_F(ExecutionTest, BLTU_Taken) {
    cpu.setReg(1, 5);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BLTU x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'110'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);
}

TEST_F(ExecutionTest, BLTU_NotTaken_UnsignedComparison) {
    cpu.setReg(1, 0xFFFFFFFF);  // Large unsigned value
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BLTU x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'110'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);  // 0xFFFFFFFF >= 10 (unsigned)
}

TEST_F(ExecutionTest, BGEU_Taken) {
    cpu.setReg(1, 10);
    cpu.setReg(2, 5);
    cpu.setPC(100);
    
    // BGEU x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'111'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 108);
}

TEST_F(ExecutionTest, BGEU_NotTaken) {
    cpu.setReg(1, 5);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BGEU x1, x2, 8
    Instruction instr = InstructionDecoder::decode(0b0'000000'00010'00001'111'0100'0'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 104);
}

TEST_F(ExecutionTest, Branch_BackwardOffset) {
    cpu.setReg(1, 10);
    cpu.setReg(2, 10);
    cpu.setPC(100);
    
    // BEQ x1, x2, -4 (backward branch)
    Instruction instr = InstructionDecoder::decode(0b1'111111'00010'00001'000'1110'1'1100011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 96);  // 100 + (-4)
}
