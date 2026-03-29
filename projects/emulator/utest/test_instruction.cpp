#include <gtest/gtest.h>
#include "Instruction.h"

class InstructionDecoderTest : public ::testing::Test {
protected:
};

// R-type: ADD x1, x2, x3
TEST_F(InstructionDecoderTest, DecodeRType_ADD) {
    // ADD x1, x2, x3
    // opcode=0110011, rd=1, funct3=000, rs1=2, rs2=3, funct7=0000000
    uint32_t instruction = 0b0000000'00011'00010'000'00001'0110011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::R_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::OP);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.rs1, 2);
    EXPECT_EQ(instr.rs2, 3);
    EXPECT_EQ(instr.funct3, 0b000);
    EXPECT_EQ(instr.funct7, 0b0000000);
}

// R-type: SUB x5, x6, x7
TEST_F(InstructionDecoderTest, DecodeRType_SUB) {
    // SUB x5, x6, x7
    // opcode=0110011, rd=5, funct3=000, rs1=6, rs2=7, funct7=0100000
    uint32_t instruction = 0b0100000'00111'00110'000'00101'0110011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::R_TYPE);
    EXPECT_EQ(instr.rd, 5);
    EXPECT_EQ(instr.rs1, 6);
    EXPECT_EQ(instr.rs2, 7);
    EXPECT_EQ(instr.funct3, 0b000);
    EXPECT_EQ(instr.funct7, 0b0100000);
}

// I-type: ADDI x1, x2, 42
TEST_F(InstructionDecoderTest, DecodeIType_ADDI) {
    // ADDI x1, x2, 42
    // opcode=0010011, rd=1, funct3=000, rs1=2, imm=42
    uint32_t instruction = 0b000000101010'00010'000'00001'0010011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::I_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::OP_IMM);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.rs1, 2);
    EXPECT_EQ(instr.funct3, 0b000);
    EXPECT_EQ(instr.imm, 42);
}

// I-type: ADDI with negative immediate
TEST_F(InstructionDecoderTest, DecodeIType_ADDI_Negative) {
    // ADDI x1, x2, -1
    // imm=-1 = 0xFFF (12 bits, sign-extended)
    uint32_t instruction = 0b111111111111'00010'000'00001'0010011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::I_TYPE);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.rs1, 2);
    EXPECT_EQ(instr.imm, -1);
}

// I-type: LW (load word)
TEST_F(InstructionDecoderTest, DecodeIType_LW) {
    // LW x5, 8(x10)
    // opcode=0000011, rd=5, funct3=010, rs1=10, imm=8
    uint32_t instruction = 0b000000001000'01010'010'00101'0000011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::I_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::LOAD);
    EXPECT_EQ(instr.rd, 5);
    EXPECT_EQ(instr.rs1, 10);
    EXPECT_EQ(instr.funct3, 0b010);
    EXPECT_EQ(instr.imm, 8);
}

// S-type: SW (store word)
TEST_F(InstructionDecoderTest, DecodeSType_SW) {
    // SW x5, 12(x10)
    // opcode=0100011, funct3=010, rs1=10, rs2=5, imm=12
    // imm[11:5]=0000000, imm[4:0]=01100
    uint32_t instruction = 0b0000000'00101'01010'010'01100'0100011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::S_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::STORE);
    EXPECT_EQ(instr.rs1, 10);
    EXPECT_EQ(instr.rs2, 5);
    EXPECT_EQ(instr.funct3, 0b010);
    EXPECT_EQ(instr.imm, 12);
}

// S-type: SW with negative offset
TEST_F(InstructionDecoderTest, DecodeSType_SW_Negative) {
    // SW x5, -4(x10)
    // imm=-4 = 0xFFC (12 bits)
    // imm[11:5]=1111111, imm[4:0]=11100
    uint32_t instruction = 0b1111111'00101'01010'010'11100'0100011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::S_TYPE);
    EXPECT_EQ(instr.rs1, 10);
    EXPECT_EQ(instr.rs2, 5);
    EXPECT_EQ(instr.imm, -4);
}

// B-type: BEQ (branch if equal)
TEST_F(InstructionDecoderTest, DecodeBType_BEQ) {
    // BEQ x1, x2, 8
    // opcode=1100011, funct3=000, rs1=1, rs2=2, imm=8
    // imm[12]=0, imm[10:5]=000000, imm[4:1]=0100, imm[11]=0
    uint32_t instruction = 0b0'000000'00010'00001'000'0100'0'1100011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::B_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::BRANCH);
    EXPECT_EQ(instr.rs1, 1);
    EXPECT_EQ(instr.rs2, 2);
    EXPECT_EQ(instr.funct3, 0b000);
    EXPECT_EQ(instr.imm, 8);
}

// B-type: BNE with negative offset
TEST_F(InstructionDecoderTest, DecodeBType_BNE_Negative) {
    // BNE x1, x2, -4
    // imm=-4 = 0x1FFC (13 bits)
    // imm[12]=1, imm[10:5]=111111, imm[4:1]=1110, imm[11]=1
    uint32_t instruction = 0b1'111111'00010'00001'001'1110'1'1100011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::B_TYPE);
    EXPECT_EQ(instr.rs1, 1);
    EXPECT_EQ(instr.rs2, 2);
    EXPECT_EQ(instr.funct3, 0b001);
    EXPECT_EQ(instr.imm, -4);
}

// U-type: LUI (load upper immediate)
TEST_F(InstructionDecoderTest, DecodeUType_LUI) {
    // LUI x5, 0x12345
    // opcode=0110111, rd=5, imm[31:12]=0x12345
    uint32_t instruction = 0x12345'000 | 0b00101'0110111;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::U_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::LUI);
    EXPECT_EQ(instr.rd, 5);
    EXPECT_EQ(instr.imm, 0x12345000);
}

// U-type: AUIPC
TEST_F(InstructionDecoderTest, DecodeUType_AUIPC) {
    // AUIPC x10, 0x80000
    uint32_t instruction = 0x80000'000 | 0b01010'0010111;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::U_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::AUIPC);
    EXPECT_EQ(instr.rd, 10);
    EXPECT_EQ(instr.imm, static_cast<int32_t>(0x80000000));
}

// J-type: JAL (jump and link)
TEST_F(InstructionDecoderTest, DecodeJType_JAL) {
    // JAL x1, 8
    // imm needs to be 8, so imm[10:1] = 00100 (4 in the shifted position)
    // Format: imm[20|10:1|11|19:12] in instruction bits [31|30:21|20|19:12]
    // For offset 8: imm[20]=0, imm[10:1]=0000000100, imm[11]=0, imm[19:12]=00000000
    uint32_t instruction = 0b0'0000000100'0'00000000'00001'1101111;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::J_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::JAL);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.imm, 8);
}

// J-type: JAL with negative offset
TEST_F(InstructionDecoderTest, DecodeJType_JAL_Negative) {
    // JAL x1, -4
    // imm=-4 in 21 bits = 0x1FFFFC
    // imm[20]=1, imm[10:1]=1111111110, imm[11]=1, imm[19:12]=11111111
    uint32_t instruction = 0b1'1111111110'1'11111111'00001'1101111;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::J_TYPE);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.imm, -4);
}

// JALR (I-type)
TEST_F(InstructionDecoderTest, DecodeIType_JALR) {
    // JALR x1, 4(x5)
    uint32_t instruction = 0b000000000100'00101'000'00001'1100111;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.format, InstructionFormat::I_TYPE);
    EXPECT_EQ(instr.opcode, Opcode::JALR);
    EXPECT_EQ(instr.rd, 1);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.imm, 4);
}

// Test all register positions
TEST_F(InstructionDecoderTest, RegisterExtraction) {
    // ADD x31, x30, x29
    uint32_t instruction = 0b0000000'11101'11110'000'11111'0110011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.rd, 31);
    EXPECT_EQ(instr.rs1, 30);
    EXPECT_EQ(instr.rs2, 29);
}

// Test funct3 extraction
TEST_F(InstructionDecoderTest, Funct3Extraction) {
    // Test with funct3 = 0b111
    uint32_t instruction = 0b0000000'00000'00000'111'00000'0110011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.funct3, 0b111);
}

// Test raw instruction storage
TEST_F(InstructionDecoderTest, RawInstructionStorage) {
    uint32_t instruction = 0x12345678;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.raw, instruction);
}

// Edge case: maximum positive I-type immediate
TEST_F(InstructionDecoderTest, ITypeMaxPositiveImm) {
    // imm = 2047 (0x7FF)
    uint32_t instruction = 0b011111111111'00000'000'00000'0010011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.imm, 2047);
}

// Edge case: maximum negative I-type immediate
TEST_F(InstructionDecoderTest, ITypeMaxNegativeImm) {
    // imm = -2048 (0x800)
    uint32_t instruction = 0b100000000000'00000'000'00000'0010011;
    
    Instruction instr = InstructionDecoder::decode(instruction);
    
    EXPECT_EQ(instr.imm, -2048);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom0_NMATVEC) {
    // opid=0, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x77
    uint32_t instruction = (0u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM0);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 0);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom0_NVRELU) {
    // opid=1, rd=x10, rs1=x11, rs2=x12, rs3=x13, opcode=0x77
    uint32_t instruction = (1u << 27) | (13u << 22) | (12u << 17) | (11u << 12) | (10u << 7) | 0x77u;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM0);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 1);
    EXPECT_EQ(instr.rd, 10);
    EXPECT_EQ(instr.rs1, 11);
    EXPECT_EQ(instr.rs2, 12);
    EXPECT_EQ(instr.rs3, 13);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NMATVECX) {
    // opid=0, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x7B
    uint32_t instruction = (0u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 0);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NVRELUX) {
    // opid=1, rd=x10, rs1=x11, rs2=x12, rs3=x13, opcode=0x7B
    uint32_t instruction = (1u << 27) | (13u << 22) | (12u << 17) | (11u << 12) | (10u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 1);
    EXPECT_EQ(instr.rd, 10);
    EXPECT_EQ(instr.rs1, 11);
    EXPECT_EQ(instr.rs2, 12);
    EXPECT_EQ(instr.rs3, 13);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NMATVEC8XP) {
    // opid=6, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x7B
    uint32_t instruction = (6u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 6);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NMATVEC8XP2) {
    // opid=7, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x7B
    uint32_t instruction = (7u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 7);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NMATVEC8XP3) {
    // opid=8, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x7B
    uint32_t instruction = (8u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 8);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}

TEST_F(InstructionDecoderTest, DecodeNeuralCustom3_NMATVEC8XP4) {
    // opid=9, rd=x6, rs1=x5, rs2=0, rs3=0, opcode=0x7B
    uint32_t instruction = (9u << 27) | (0u << 22) | (0u << 17) | (5u << 12) | (6u << 7) | 0x7Bu;
    Instruction instr = InstructionDecoder::decode(instruction);
    EXPECT_EQ(instr.opcode, Opcode::CUSTOM3);
    EXPECT_EQ(instr.format, InstructionFormat::N_TYPE);
    EXPECT_EQ(instr.neural_op, 9);
    EXPECT_EQ(instr.rd, 6);
    EXPECT_EQ(instr.rs1, 5);
    EXPECT_EQ(instr.rs2, 0);
    EXPECT_EQ(instr.rs3, 0);
}
