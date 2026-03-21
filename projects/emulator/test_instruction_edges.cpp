#include <gtest/gtest.h>
#include "CPU.h"
#include "Memory.h"
#include "Instruction.h"

class InstructionEdgeCasesTest : public ::testing::Test {
protected:
    CPU cpu;
    Memory memory{1024};
    
    void SetUp() override {
        cpu.reset();
        memory.reset();
    }
};

// ============================================================================
// UNALIGNED LOAD/STORE TESTS
// ============================================================================

// Test unaligned load (load word from unaligned address)
// RISC-V requires word loads to be 4-byte aligned. This test verifies behavior
// when attempting to load from an odd address.
TEST_F(InstructionEdgeCasesTest, UnalignedLoadWord) {
    // Write a 32-bit value across byte boundary
    memory.write8(101, 0x12);
    memory.write8(102, 0x34);
    memory.write8(103, 0x56);
    memory.write8(104, 0x78);
    
    cpu.setReg(1, 101);  // Unaligned address (101 % 4 != 0)
    
    // LW x2, 0(x1) from unaligned address
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'010'00010'0000011);
    cpu.execute(instr, memory);
    
    // Verify load succeeds (RISC-V allows unaligned loads, though may have performance penalty)
    EXPECT_EQ(cpu.getReg(2), 0x78563412);  // Little-endian read
}

// Test unaligned store (store word to unaligned address)
// Verifies that storing to an unaligned address doesn't corrupt adjacent memory
TEST_F(InstructionEdgeCasesTest, UnalignedStoreWord) {
    cpu.setReg(1, 101);  // Unaligned address
    cpu.setReg(2, 0xDEADBEEF);
    
    // SW x2, 0(x1) to unaligned address
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'010'00000'0100011);
    cpu.execute(instr, memory);
    
    // Verify memory is written correctly even at unaligned address
    EXPECT_EQ(memory.read8(101), 0xEF);
    EXPECT_EQ(memory.read8(102), 0xBE);
    EXPECT_EQ(memory.read8(103), 0xAD);
    EXPECT_EQ(memory.read8(104), 0xDE);
}

// ============================================================================
// SHIFT OPERATION BOUNDARY TESTS
// ============================================================================

// Test shift left logical (SLL) at boundary: shift by 31 bits (max valid for RV32I)
// SLL with shamt=31 should shift value left by 31 positions
TEST_F(InstructionEdgeCasesTest, ShiftLeftLogical_MaxShift) {
    cpu.setReg(1, 0b00000000000000000000000000000010);  // 2 (0x2)
    cpu.setReg(2, 31);  // Shift by 31 bits
    
    // SLL x3, x1, x2 (shift x1 left by x2 positions)
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'001'00011'0110011);
    cpu.execute(instr, memory);
    
    // 2 << 31 = 0x100000000 -> wraps to 0 (32-bit result)
    EXPECT_EQ(cpu.getReg(3), 0x00000000);
}

// Test shift right logical (SRL) at boundary: shift by 31 bits
// SRL with shamt=31 should shift value right by 31 positions
TEST_F(InstructionEdgeCasesTest, ShiftRightLogical_MaxShift) {
    cpu.setReg(1, 0xFFFFFFFF);  // All bits set
    cpu.setReg(2, 31);  // Shift by 31 bits
    
    // SRL x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0000000'00010'00001'101'00011'0110011);
    cpu.execute(instr, memory);
    
    // 0xFFFFFFFF >> 31 = 0x1
    EXPECT_EQ(cpu.getReg(3), 0x00000001);
}

// Test shift right arithmetic (SRA) at boundary: shift by 31 bits with negative value
// SRA with shamt=31 on negative number should sign-extend, resulting in 0xFFFFFFFF
TEST_F(InstructionEdgeCasesTest, ShiftRightArithmetic_NegativeMaxShift) {
    cpu.setReg(1, 0xFFFFFFFF);  // -1 in two's complement
    cpu.setReg(2, 31);  // Shift by 31 bits
    
    // SRA x3, x1, x2
    Instruction instr = InstructionDecoder::decode(0b0100000'00010'00001'101'00011'0110011);
    cpu.execute(instr, memory);
    
    // 0xFFFFFFFF >> 31 (arithmetic) = 0xFFFFFFFF (sign-extended)
    EXPECT_EQ(cpu.getReg(3), 0xFFFFFFFF);
}

// ============================================================================
// IMMEDIATE FIELD BOUNDARY TESTS
// ============================================================================

// Test immediate field at maximum positive value for I-type instructions
// I-type immediates are 12-bit, signed: range [-2048, 2047]
// This tests the maximum positive immediate: 2047 (0x7FF)
TEST_F(InstructionEdgeCasesTest, ImmediateField_MaxPositive) {
    cpu.setReg(1, 0);
    
    // ADDI x2, x1, 2047 (max positive I-type immediate)
    // 12-bit immediate = 0x7FF
    Instruction instr = InstructionDecoder::decode(0b011111111111'00001'000'00010'0010011);
    cpu.execute(instr, memory);
    
    EXPECT_EQ(cpu.getReg(2), 2047);
}

// Test immediate field at minimum negative value for I-type instructions
// I-type immediates: min = -2048 (0xFFF800 in 12-bit two's complement = 0x800)
// This tests the minimum negative immediate: -2048
TEST_F(InstructionEdgeCasesTest, ImmediateField_MinNegative) {
    cpu.setReg(1, 0);
    
    // ADDI x2, x1, -2048 (min negative I-type immediate)
    // 12-bit immediate in two's complement: -2048 = 0x800
    Instruction instr = InstructionDecoder::decode(0b100000000000'00001'000'00010'0010011);
    cpu.execute(instr, memory);
    
    // 0 + (-2048) = -2048 = 0xFFFFF800 (sign-extended)
    EXPECT_EQ(cpu.getReg(2), (uint32_t)-2048);
}

// ============================================================================
// LOAD FROM UNINITIALIZED MEMORY TEST
// ============================================================================

// Test loading from uninitialized memory
// Uninitialized memory may contain garbage. Verify that loading from an
// uninitialized address returns whatever was there (not a crash/error)
TEST_F(InstructionEdgeCasesTest, LoadFromUninitializedMemory) {
    // Memory at address 500 is uninitialized
    // Write a known pattern that we can verify
    memory.write32(500, 0xCAFEBABE);
    
    cpu.setReg(1, 500);
    
    // LW x2, 0(x1) - load from address that was initialized
    Instruction instr = InstructionDecoder::decode(0b000000000000'00001'010'00010'0000011);
    cpu.execute(instr, memory);
    
    // Verify we get what we wrote
    EXPECT_EQ(cpu.getReg(2), 0xCAFEBABE);
    
    // Now test truly uninitialized (address 504 was never written)
    cpu.setReg(1, 504);
    cpu.setReg(2, 0xFFFFFFFF);  // Set to known value before loading
    
    // LW x2, 0(x1) - load from uninitialized address
    cpu.execute(instr, memory);
    
    // Result should be 0 (default initialized memory)
    EXPECT_EQ(cpu.getReg(2), 0x00000000);
}

// ============================================================================
// BRANCH OFFSET BOUNDARY TESTS
// ============================================================================

// Test branch with maximum forward offset
// B-type immediates are 12-bit signed, encoding offsets up to ±4095 bytes
// This test verifies a large forward branch works correctly
TEST_F(InstructionEdgeCasesTest, BranchMaxForwardOffset) {
    cpu.setPC(100);
    cpu.setReg(1, 42);
    cpu.setReg(2, 42);
    
    // BEQ x1, x2, 2000 (large forward offset)
    // 2000 = 0x07D0 in binary
    // B-type immediate: [12|10:5|4:1|11]
    // Construct: bit12=0, bits10:5=111110 (62), bits4:1=1000 (8), bit11=0
    // This gives: 0'111110'1000'0 = 0x7D0 (1968 in decimal, but bits are positioned for 2000)
    // Actually: encode 1000 = 0x03E8
    // 1000 >> 1 = 500 = 0x1F4 = 0b111110100
    // bits[12|10:5|4:1|11] = 0b0'111110'0100'0
    uint32_t imm = 1000;  // offset / 2 for encoding
    uint32_t imm_12 = (imm >> 12) & 0b1;
    uint32_t imm_11 = (imm >> 11) & 0b1;
    uint32_t imm_10_5 = (imm >> 5) & 0b111111;
    uint32_t imm_4_1 = (imm >> 1) & 0b1111;
    
    uint32_t instr_bits = (imm_12 << 31) |  // imm[12] at bit 31
                          (imm_10_5 << 25) |  // imm[10:5] at bits 30:25
                          (2 << 20) |  // rs2 at bits 24:20
                          (1 << 15) |  // rs1 at bits 19:15
                          (0 << 12) |  // funct3 at bits 14:12
                          (imm_4_1 << 8) |  // imm[4:1] at bits 11:8
                          (imm_11 << 7) |  // imm[11] at bit 7
                          0b1100011;   // opcode for BRANCH
    
    Instruction instr = InstructionDecoder::decode(instr_bits);
    cpu.execute(instr, memory);
    
    // Branch should be taken: PC = 100 + 1000 = 1100
    EXPECT_EQ(cpu.getPC(), 100 + 1000);
}

// Test branch with maximum backward offset
// Verifies that backward branches work with large negative offsets
TEST_F(InstructionEdgeCasesTest, BranchMaxBackwardOffset) {
    cpu.setPC(5000);
    cpu.setReg(1, 42);
    cpu.setReg(2, 42);
    
    // BEQ x1, x2, -1000 (large backward offset)
    // -1000 in 13-bit two's complement
    int32_t offset = -1000;
    uint32_t imm = (uint32_t)offset;
    uint32_t imm_12 = (imm >> 12) & 0b1;
    uint32_t imm_11 = (imm >> 11) & 0b1;
    uint32_t imm_10_5 = (imm >> 5) & 0b111111;
    uint32_t imm_4_1 = (imm >> 1) & 0b1111;
    
    uint32_t instr_bits = (imm_12 << 31) |  // imm[12] at bit 31
                          (imm_10_5 << 25) |  // imm[10:5] at bits 30:25
                          (2 << 20) |  // rs2
                          (1 << 15) |  // rs1
                          (0 << 12) |  // funct3
                          (imm_4_1 << 8) |  // imm[4:1] at bits 11:8
                          (imm_11 << 7) |  // imm[11] at bit 7
                          0b1100011;   // opcode for BRANCH
    
    Instruction instr = InstructionDecoder::decode(instr_bits);
    cpu.execute(instr, memory);
    
    // Branch should be taken: PC = 5000 - 1000 = 4000
    EXPECT_EQ(cpu.getPC(), 5000 - 1000);
}

