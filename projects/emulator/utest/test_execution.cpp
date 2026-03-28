#include <gtest/gtest.h>
#include "CPU.h"
#include "Memory.h"
#include "Instruction.h"
#include <cstring>

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

// Jump operations

TEST_F(ExecutionTest, JAL_Forward) {
    cpu.setPC(100);
    
    // JAL x1, 8
    Instruction instr = InstructionDecoder::decode(0b0'0000000100'0'00000000'00001'1101111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(1), 104);  // Return address: PC + 4
    EXPECT_EQ(cpu.getPC(), 108);    // Jump target: PC + 8
}

TEST_F(ExecutionTest, JAL_Backward) {
    cpu.setPC(100);
    
    // JAL x1, -4
    Instruction instr = InstructionDecoder::decode(0b1'1111111110'1'11111111'00001'1101111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(1), 104);  // Return address
    EXPECT_EQ(cpu.getPC(), 96);     // Jump target: 100 + (-4)
}

TEST_F(ExecutionTest, JAL_ToX0) {
    cpu.setPC(100);
    
    // JAL x0, 8 (unconditional jump without saving return address)
    Instruction instr = InstructionDecoder::decode(0b0'0000000100'0'00000000'00000'1101111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(0), 0);    // x0 always zero
    EXPECT_EQ(cpu.getPC(), 108);
}

TEST_F(ExecutionTest, JALR_Basic) {
    cpu.setReg(5, 200);
    cpu.setPC(100);
    
    // JALR x1, 4(x5)
    Instruction instr = InstructionDecoder::decode(0b000000000100'00101'000'00001'1100111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(1), 104);  // Return address: PC + 4
    EXPECT_EQ(cpu.getPC(), 204);    // Jump target: 200 + 4
}

TEST_F(ExecutionTest, JALR_ZeroOffset) {
    cpu.setReg(10, 300);
    cpu.setPC(100);
    
    // JALR x2, 0(x10)
    Instruction instr = InstructionDecoder::decode(0b000000000000'01010'000'00010'1100111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 104);
    EXPECT_EQ(cpu.getPC(), 300);
}

TEST_F(ExecutionTest, JALR_ClearLSB) {
    cpu.setReg(5, 201);  // Odd address
    cpu.setPC(100);
    
    // JALR x1, 0(x5) - should clear LSB
    Instruction instr = InstructionDecoder::decode(0b000000000000'00101'000'00001'1100111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getPC(), 200);  // 201 & ~1 = 200
}

TEST_F(ExecutionTest, JALR_SameRegister) {
    cpu.setReg(5, 200);
    cpu.setPC(100);
    
    // JALR x5, 4(x5) - use same register for source and dest
    Instruction instr = InstructionDecoder::decode(0b000000000100'00101'000'00101'1100111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(5), 104);  // Return address written after reading rs1
    EXPECT_EQ(cpu.getPC(), 204);
}

// Upper immediate operations

TEST_F(ExecutionTest, LUI) {
    cpu.setPC(100);
    
    // LUI x5, 0x12345 (upper 20 bits)
    Instruction instr = InstructionDecoder::decode(0x12345'000 | 0b00101'0110111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(5), 0x12345000);
    EXPECT_EQ(cpu.getPC(), 104);
}

TEST_F(ExecutionTest, LUI_MaxValue) {
    // LUI x10, 0xFFFFF
    Instruction instr = InstructionDecoder::decode(0xFFFFF'000 | 0b01010'0110111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(10), 0xFFFFF000);
}

TEST_F(ExecutionTest, LUI_Zero) {
    cpu.setReg(3, 0x12345678);
    
    // LUI x3, 0
    Instruction instr = InstructionDecoder::decode(0x00000'000 | 0b00011'0110111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(3), 0);
}

TEST_F(ExecutionTest, AUIPC) {
    cpu.setPC(100);
    
    // AUIPC x5, 0x1000
    Instruction instr = InstructionDecoder::decode(0x01000'000 | 0b00101'0010111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(5), 100 + 0x01000000);
    EXPECT_EQ(cpu.getPC(), 104);
}

TEST_F(ExecutionTest, AUIPC_NegativeOffset) {
    cpu.setPC(0x10000);
    
    // AUIPC x10, 0x80000 (sign bit set)
    Instruction instr = InstructionDecoder::decode(0x80000'000 | 0b01010'0010111);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(10), 0x10000 + 0x80000000);
}

// Combined instruction sequences

TEST_F(ExecutionTest, LoadUpperAndAddImmediate) {
    cpu.setPC(0);
    
    // LUI x5, 0x12345
    Instruction instr1 = InstructionDecoder::decode(0x12345'000 | 0b00101'0110111);
    cpu.execute(instr1, memory);
    EXPECT_EQ(cpu.getReg(5), 0x12345000);
    
    // ADDI x5, x5, 0x678
    Instruction instr2 = InstructionDecoder::decode(0b011001111000'00101'000'00101'0010011);
    cpu.execute(instr2, memory);
    EXPECT_EQ(cpu.getReg(5), 0x12345678);
}

// Neural custom op execution
TEST_F(ExecutionTest, NeuralNVReLUExecutesAndSetsStatus) {
    const uint32_t src = 0x100;
    const uint32_t dst = 0x200;
    const float in_vals[3] = {-1.0f, 0.0f, 2.5f};
    for (int i = 0; i < 3; ++i) {
        uint32_t bits;
        std::memcpy(&bits, &in_vals[i], sizeof(bits));
        memory.write32(src + i * 4, bits);
    }

    cpu.setReg(11, dst); // rs1
    cpu.setReg(12, src); // rs2
    cpu.setReg(13, 3);   // rs3

    // opid=1 (nvrelu), rd=x10, rs1=x11, rs2=x12, rs3=x13
    uint32_t raw = (1u << 27) | (13u << 22) | (12u << 17) | (11u << 12) | (10u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(10), 0u); // status ok
    EXPECT_EQ(memory.read32(dst + 0), 0x00000000u);
    EXPECT_EQ(memory.read32(dst + 4), 0x00000000u);
    EXPECT_EQ(memory.read32(dst + 8), 0x40200000u); // 2.5f
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralNMatvecUsesDescriptorAndSetsStatus) {
    const uint32_t desc = 0x100;
    const uint32_t input = 0x140;
    const uint32_t weights = 0x180;
    const uint32_t bias = 0x1C0;
    const uint32_t output = 0x200;

    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    // input [1,2]
    write_f32(input + 0, 1.0f);
    write_f32(input + 4, 2.0f);
    // weights i-major: [1,2,3,4]
    write_f32(weights + 0, 1.0f);
    write_f32(weights + 4, 2.0f);
    write_f32(weights + 8, 3.0f);
    write_f32(weights + 12, 4.0f);
    // bias [0,0]
    write_f32(bias + 0, 0.0f);
    write_f32(bias + 4, 0.0f);

    memory.write32(desc + 0x00, input);
    memory.write32(desc + 0x04, weights);
    memory.write32(desc + 0x08, bias);
    memory.write32(desc + 0x0C, output);
    memory.write32(desc + 0x10, 2); // input_len
    memory.write32(desc + 0x14, 2); // output_len
    memory.write32(desc + 0x18, 0); // flags
    memory.write32(desc + 0x1C, 0);

    cpu.setReg(5, desc); // rs1 for nmatvec
    // opid=0 (nmatvec), rd=x6, rs1=x5
    uint32_t raw = (0u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(6), 0u); // status ok
    EXPECT_EQ(memory.read32(output + 0), 0x40E00000u); // 7.0
    EXPECT_EQ(memory.read32(output + 4), 0x41200000u); // 10.0
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralNVSigPwlExecutesAndSetsStatus) {
    const uint32_t src = 0x280;
    const uint32_t dst = 0x2C0;
    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    write_f32(src + 0, -5.0f); // -> 0.0
    write_f32(src + 4, 0.0f);  // -> 0.5
    write_f32(src + 8, 5.0f);  // -> 1.0

    cpu.setReg(18, dst); // rs1
    cpu.setReg(19, src); // rs2
    cpu.setReg(20, 3);   // rs3

    // opid=2, rd=x5, rs1=x18, rs2=x19, rs3=x20
    uint32_t raw = (2u << 27) | (20u << 22) | (19u << 17) | (18u << 12) | (5u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(5), 0u); // status ok
    EXPECT_EQ(memory.read32(dst + 0), 0x00000000u); // 0.0
    EXPECT_EQ(memory.read32(dst + 4), 0x3F000000u); // 0.5
    EXPECT_EQ(memory.read32(dst + 8), 0x3F800000u); // 1.0
}

TEST_F(ExecutionTest, NeuralNVClampU8ExecutesAndSetsStatus) {
    const uint32_t src = 0x300;
    const uint32_t dst = 0x340;
    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };
    write_f32(src + 0, 0.0f);
    write_f32(src + 4, 0.5f);
    write_f32(src + 8, 1.0f);

    cpu.setReg(10, dst); // rs1
    cpu.setReg(11, src); // rs2
    cpu.setReg(12, 3);   // rs3

    // opid=3, rd=x8, rs1=x10, rs2=x11, rs3=x12
    uint32_t raw = (3u << 27) | (12u << 22) | (11u << 17) | (10u << 12) | (8u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(8), 0u); // status ok
    EXPECT_EQ(memory.read8(dst + 0), 0u);
    EXPECT_EQ(memory.read8(dst + 1), 127u);
    EXPECT_EQ(memory.read8(dst + 2), 255u);
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3NVReLUExecutesAndSetsStatus) {
    const uint32_t src = 0x100;
    const uint32_t dst = 0x200;
    const float in_vals[3] = {-1.0f, 0.0f, 2.5f};
    for (int i = 0; i < 3; ++i) {
        uint32_t bits;
        std::memcpy(&bits, &in_vals[i], sizeof(bits));
        memory.write32(src + i * 4, bits);
    }

    cpu.setReg(11, dst); // rs1
    cpu.setReg(12, src); // rs2
    cpu.setReg(13, 3);   // rs3

    // opid=1 (nvrelux), rd=x10, rs1=x11, rs2=x12, rs3=x13, opcode=0x7B
    uint32_t raw = (1u << 27) | (13u << 22) | (12u << 17) | (11u << 12) | (10u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(10), 0u); // status ok
    EXPECT_EQ(memory.read32(dst + 0), 0x00000000u);
    EXPECT_EQ(memory.read32(dst + 4), 0x00000000u);
    EXPECT_EQ(memory.read32(dst + 8), 0x40200000u); // 2.5f
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3NMatvecExecutesAndSetsStatus) {
    const uint32_t desc = 0x100;
    const uint32_t input = 0x140;
    const uint32_t weights = 0x180;
    const uint32_t bias = 0x1C0;
    const uint32_t output = 0x200;

    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    write_f32(input + 0, 1.0f);
    write_f32(input + 4, 2.0f);
    write_f32(weights + 0, 1.0f);
    write_f32(weights + 4, 2.0f);
    write_f32(weights + 8, 3.0f);
    write_f32(weights + 12, 4.0f);
    write_f32(bias + 0, 0.0f);
    write_f32(bias + 4, 0.0f);

    memory.write32(desc + 0x00, input);
    memory.write32(desc + 0x04, weights);
    memory.write32(desc + 0x08, bias);
    memory.write32(desc + 0x0C, output);
    memory.write32(desc + 0x10, 2);
    memory.write32(desc + 0x14, 2);
    memory.write32(desc + 0x18, 0);
    memory.write32(desc + 0x1C, 0);

    cpu.setReg(5, desc); // rs1 for nmatvecx
    // opid=0 (nmatvecx), rd=x6, rs1=x5, opcode=0x7B
    uint32_t raw = (0u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(6), 0u); // status ok
    EXPECT_EQ(memory.read32(output + 0), 0x40E00000u); // 7.0
    EXPECT_EQ(memory.read32(output + 4), 0x41200000u); // 10.0
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3NMatvec4xExecutesAndSetsStatus) {
    const uint32_t desc = 0x100;
    const uint32_t input = 0x140;
    const uint32_t weights = 0x180;
    const uint32_t bias = 0x1C0;
    const uint32_t output = 0x200;

    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    write_f32(input + 0, 1.0f);
    write_f32(input + 4, 2.0f);
    write_f32(weights + 0, 1.0f);
    write_f32(weights + 4, 2.0f);
    write_f32(weights + 8, 3.0f);
    write_f32(weights + 12, 4.0f);
    write_f32(bias + 0, 0.0f);
    write_f32(bias + 4, 0.0f);

    memory.write32(desc + 0x00, input);
    memory.write32(desc + 0x04, weights);
    memory.write32(desc + 0x08, bias);
    memory.write32(desc + 0x0C, output);
    memory.write32(desc + 0x10, 2);
    memory.write32(desc + 0x14, 2);
    memory.write32(desc + 0x18, 0);
    memory.write32(desc + 0x1C, 0);

    cpu.setReg(5, desc); // rs1 for nmatvec4x
    // opid=4 (nmatvec4x), rd=x6, rs1=x5, opcode=0x7B
    uint32_t raw = (4u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(6), 0u); // status ok
    EXPECT_EQ(memory.read32(output + 0), 0x40E00000u); // 7.0
    EXPECT_EQ(memory.read32(output + 4), 0x41200000u); // 10.0
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3NMatvec8xExecutesAndSetsStatus) {
    const uint32_t desc = 0x100;
    const uint32_t input = 0x140;
    const uint32_t weights = 0x180;
    const uint32_t bias = 0x1C0;
    const uint32_t output = 0x200;

    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    write_f32(input + 0, 1.0f);
    write_f32(input + 4, 2.0f);
    write_f32(weights + 0, 1.0f);
    write_f32(weights + 4, 2.0f);
    write_f32(weights + 8, 3.0f);
    write_f32(weights + 12, 4.0f);
    write_f32(bias + 0, 0.0f);
    write_f32(bias + 4, 0.0f);

    memory.write32(desc + 0x00, input);
    memory.write32(desc + 0x04, weights);
    memory.write32(desc + 0x08, bias);
    memory.write32(desc + 0x0C, output);
    memory.write32(desc + 0x10, 2);
    memory.write32(desc + 0x14, 2);
    memory.write32(desc + 0x18, 0);
    memory.write32(desc + 0x1C, 0);

    cpu.setReg(5, desc); // rs1 for nmatvec8x
    // opid=5 (nmatvec8x), rd=x6, rs1=x5, opcode=0x7B
    uint32_t raw = (5u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(6), 0u); // status ok
    EXPECT_EQ(memory.read32(output + 0), 0x40E00000u); // 7.0
    EXPECT_EQ(memory.read32(output + 4), 0x41200000u); // 10.0
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3NMatvec8xpExecutesAndSetsStatus) {
    const uint32_t desc = 0x100;
    const uint32_t input = 0x140;
    const uint32_t weights = 0x180;
    const uint32_t bias = 0x1C0;
    const uint32_t output = 0x200;

    auto write_f32 = [&](uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, sizeof(bits));
        memory.write32(addr, bits);
    };

    write_f32(input + 0, 1.0f);
    write_f32(input + 4, 2.0f);
    write_f32(weights + 0, 1.0f);
    write_f32(weights + 4, 2.0f);
    write_f32(weights + 8, 3.0f);
    write_f32(weights + 12, 4.0f);
    write_f32(bias + 0, 0.0f);
    write_f32(bias + 4, 0.0f);

    memory.write32(desc + 0x00, input);
    memory.write32(desc + 0x04, weights);
    memory.write32(desc + 0x08, bias);
    memory.write32(desc + 0x0C, output);
    memory.write32(desc + 0x10, 2);
    memory.write32(desc + 0x14, 2);
    memory.write32(desc + 0x18, 0);
    memory.write32(desc + 0x1C, 0);

    cpu.setReg(5, desc); // rs1 for nmatvec8xp
    // opid=6 (nmatvec8xp), rd=x6, rs1=x5, opcode=0x7B
    uint32_t raw = (6u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    cpu.execute(instr, memory);

    EXPECT_EQ(cpu.getReg(6), 0u); // status ok
    EXPECT_EQ(memory.read32(output + 0), 0x40E00000u); // 7.0
    EXPECT_EQ(memory.read32(output + 4), 0x41200000u); // 10.0
    EXPECT_EQ(cpu.getPC(), 4u);
}

TEST_F(ExecutionTest, NeuralCustom3UnknownOpFailsLoud) {
    // opid=31 unsupported, opcode=0x7B
    const uint32_t raw = (31u << 27) | (10u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(raw);
    EXPECT_THROW(cpu.execute(instr, memory), std::runtime_error);
}

TEST_F(ExecutionTest, NeuralCustom0UnknownOpFailsLoud) {
    // opid=31 unsupported, opcode=0x77
    const uint32_t raw = (31u << 27) | (10u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(raw);
    EXPECT_THROW(cpu.execute(instr, memory), std::runtime_error);
}

TEST_F(ExecutionTest, FunctionCallReturn) {
    cpu.setPC(100);
    cpu.setReg(10, 500);
    
    // JAL x1, 20 (call function at PC + 20)
    Instruction instr1 = InstructionDecoder::decode(0b0'0000001010'0'00000000'00001'1101111);
    cpu.execute(instr1, memory);
    EXPECT_EQ(cpu.getReg(1), 104);  // Return address
    EXPECT_EQ(cpu.getPC(), 120);
    
    // Simulate some work...
    cpu.setReg(2, 42);
    
    // JALR x0, 0(x1) (return using saved return address)
    Instruction instr2 = InstructionDecoder::decode(0b000000000000'00001'000'00000'1100111);
    cpu.execute(instr2, memory);
    EXPECT_EQ(cpu.getPC(), 104);  // Back to return address
}
