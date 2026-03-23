#include <gtest/gtest.h>
#include <cmath>
#include <cstring>
#include <limits>
#include "Emulator.h"

class FPInstructionTest : public ::testing::Test {
protected:
    Emulator emulator{64 * 1024};  // 64 KB is sufficient for FP instruction tests
    
    void SetUp() override {
        emulator.reset();
    }
    
    // Helper to execute single instruction
    void executeInstr(uint32_t instr) {
        std::vector<uint32_t> program = {instr};
        emulator.loadProgram(program, 0);
        emulator.step();
    }
    
    // Helper to encode FLW instruction
    uint32_t encodeFLW(uint8_t rd, uint8_t rs1, int16_t offset) {
        uint32_t instr = 0b0000111;  // LOAD_FP opcode
        instr |= (rd & 0x1F) << 7;
        instr |= 0b010 << 12;  // funct3 = 0b010 for FLW
        instr |= (rs1 & 0x1F) << 15;
        instr |= (offset & 0xFFF) << 20;
        return instr;
    }
    
    // Helper to encode FSW instruction
    uint32_t encodeFSW(uint8_t rs2, uint8_t rs1, int16_t offset) {
        uint32_t instr = 0b0100111;  // STORE_FP opcode
        instr |= (offset & 0x1F) << 7;
        instr |= 0b010 << 12;  // funct3 = 0b010 for FSW
        instr |= (rs1 & 0x1F) << 15;
        instr |= (rs2 & 0x1F) << 20;
        instr |= ((offset >> 5) & 0x7F) << 25;
        return instr;
    }
    
    // Helper to encode R-type FP instructions
    uint32_t encodeFPR(uint8_t funct7, uint8_t rd, uint8_t funct3, uint8_t rs1, uint8_t rs2) {
        uint32_t instr = 0b1010011;  // OP_FP opcode
        instr |= (rd & 0x1F) << 7;
        instr |= (funct3 & 0x7) << 12;
        instr |= (rs1 & 0x1F) << 15;
        instr |= (rs2 & 0x1F) << 20;
        instr |= (funct7 & 0x7F) << 25;
        return instr;
    }
    
    // Helper to get float as bits
    uint32_t floatToBits(float f) {
        uint32_t bits;
        std::memcpy(&bits, &f, sizeof(uint32_t));
        return bits;
    }
    
    // Helper to get bits as float
    float bitsToFloat(uint32_t bits) {
        float f;
        std::memcpy(&f, &bits, sizeof(float));
        return f;
    }
};

// Test FLW (Floating-Point Load Word)
TEST_F(FPInstructionTest, FLW_LoadsFloat) {
    // Store π as 32-bit float at address 0x1000
    float pi = 3.14159265f;
    emulator.getMemory().write32(0x1000, floatToBits(pi));
    
    // Set x1 = 0x1000
    emulator.getCPU().setReg(1, 0x1000);
    
    // FLW f2, 0(x1)
    uint32_t instr = encodeFLW(2, 1, 0);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(2);
    EXPECT_FLOAT_EQ(result, pi);
}

TEST_F(FPInstructionTest, FLW_WithOffset) {
    // Store value at 0x1000 + 12 = 0x100C
    float value = 2.71828f;  // e
    emulator.getMemory().write32(0x100C, floatToBits(value));
    
    // Set x1 = 0x1000
    emulator.getCPU().setReg(1, 0x1000);
    
    // FLW f3, 12(x1)
    uint32_t instr = encodeFLW(3, 1, 12);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, value);
}

TEST_F(FPInstructionTest, FLW_NegativeOffset) {
    // Store value at 0x2000 - 4 = 0x1FFC
    float value = -1.5f;
    emulator.getMemory().write32(0x1FFC, floatToBits(value));
    
    // Set x1 = 0x2000
    emulator.getCPU().setReg(1, 0x2000);
    
    // FLW f4, -4(x1)
    uint32_t instr = encodeFLW(4, 1, -4);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, value);
}

// Test FSW (Floating-Point Store Word)
TEST_F(FPInstructionTest, FSW_StoresFloat) {
    float value = 42.5f;
    emulator.getCPU().setFPReg(5, value);
    
    // Set x2 = 0x3000
    emulator.getCPU().setReg(2, 0x3000);
    
    // FSW f5, 0(x2)
    uint32_t instr = encodeFSW(5, 2, 0);
    executeInstr(instr);
    
    uint32_t stored = emulator.getMemory().read32(0x3000);
    float result = bitsToFloat(stored);
    EXPECT_FLOAT_EQ(result, value);
}

TEST_F(FPInstructionTest, FSW_WithOffset) {
    float value = -99.99f;
    emulator.getCPU().setFPReg(6, value);
    
    // Set x3 = 0x4000
    emulator.getCPU().setReg(3, 0x4000);
    
    // FSW f6, 8(x3)
    uint32_t instr = encodeFSW(6, 3, 8);
    executeInstr(instr);
    
    uint32_t stored = emulator.getMemory().read32(0x4008);
    float result = bitsToFloat(stored);
    EXPECT_FLOAT_EQ(result, value);
}

// Test FADD.S (Floating-Point Addition)
TEST_F(FPInstructionTest, FADD_S_AddsFloats) {
    emulator.getCPU().setFPReg(1, 2.5f);
    emulator.getCPU().setFPReg(2, 3.5f);
    
    // FADD.S f3, f1, f2
    uint32_t instr = encodeFPR(0b0000000, 3, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, 6.0f);
}

TEST_F(FPInstructionTest, FADD_S_NegativeNumbers) {
    emulator.getCPU().setFPReg(1, -5.25f);
    emulator.getCPU().setFPReg(2, 3.75f);
    
    // FADD.S f4, f1, f2
    uint32_t instr = encodeFPR(0b0000000, 4, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, -1.5f);
}

TEST_F(FPInstructionTest, FADD_S_Zero) {
    emulator.getCPU().setFPReg(1, 0.0f);
    emulator.getCPU().setFPReg(2, 7.5f);
    
    // FADD.S f5, f1, f2
    uint32_t instr = encodeFPR(0b0000000, 5, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(5);
    EXPECT_FLOAT_EQ(result, 7.5f);
}

// Test FSUB.S (Floating-Point Subtraction)
TEST_F(FPInstructionTest, FSUB_S_SubtractsFloats) {
    emulator.getCPU().setFPReg(1, 10.0f);
    emulator.getCPU().setFPReg(2, 3.5f);
    
    // FSUB.S f3, f1, f2
    uint32_t instr = encodeFPR(0b0000100, 3, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, 6.5f);
}

TEST_F(FPInstructionTest, FSUB_S_ResultNegative) {
    emulator.getCPU().setFPReg(1, 3.0f);
    emulator.getCPU().setFPReg(2, 5.0f);
    
    // FSUB.S f4, f1, f2
    uint32_t instr = encodeFPR(0b0000100, 4, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, -2.0f);
}

// Test FMUL.S (Floating-Point Multiplication)
TEST_F(FPInstructionTest, FMUL_S_MultipliesFloats) {
    emulator.getCPU().setFPReg(1, 2.0f);
    emulator.getCPU().setFPReg(2, 3.5f);
    
    // FMUL.S f3, f1, f2
    uint32_t instr = encodeFPR(0b0001000, 3, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, 7.0f);
}

TEST_F(FPInstructionTest, FMUL_S_NegativeResult) {
    emulator.getCPU().setFPReg(1, -4.0f);
    emulator.getCPU().setFPReg(2, 2.5f);
    
    // FMUL.S f4, f1, f2
    uint32_t instr = encodeFPR(0b0001000, 4, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, -10.0f);
}

TEST_F(FPInstructionTest, FMUL_S_ByZero) {
    emulator.getCPU().setFPReg(1, 5.5f);
    emulator.getCPU().setFPReg(2, 0.0f);
    
    // FMUL.S f5, f1, f2
    uint32_t instr = encodeFPR(0b0001000, 5, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(5);
    EXPECT_FLOAT_EQ(result, 0.0f);
}

TEST_F(FPInstructionTest, FMUL_S_VerySmall) {
    emulator.getCPU().setFPReg(1, 1e-20f);
    emulator.getCPU().setFPReg(2, 1e-20f);
    
    // FMUL.S f6, f1, f2
    uint32_t instr = encodeFPR(0b0001000, 6, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(6);
    EXPECT_FLOAT_EQ(result, 1e-40f);
}

// Test FMAX.S (Floating-Point Maximum)
TEST_F(FPInstructionTest, FMAX_S_ReturnsMaximum) {
    emulator.getCPU().setFPReg(1, 5.0f);
    emulator.getCPU().setFPReg(2, 3.0f);
    
    // FMAX.S f3, f1, f2
    uint32_t instr = encodeFPR(0b0010100, 3, 0b001, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, 5.0f);
}

TEST_F(FPInstructionTest, FMAX_S_ReverseOrder) {
    emulator.getCPU().setFPReg(1, 2.0f);
    emulator.getCPU().setFPReg(2, 8.0f);
    
    // FMAX.S f4, f1, f2
    uint32_t instr = encodeFPR(0b0010100, 4, 0b001, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, 8.0f);
}

TEST_F(FPInstructionTest, FMAX_S_ReLUPattern) {
    // ReLU: max(x, 0)
    emulator.getCPU().setFPReg(1, -3.5f);
    emulator.getCPU().setFPReg(2, 0.0f);
    
    // FMAX.S f5, f1, f2
    uint32_t instr = encodeFPR(0b0010100, 5, 0b001, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(5);
    EXPECT_FLOAT_EQ(result, 0.0f);
}

TEST_F(FPInstructionTest, FMAX_S_ReLUPositive) {
    // ReLU: max(x, 0) with positive x
    emulator.getCPU().setFPReg(1, 7.25f);
    emulator.getCPU().setFPReg(2, 0.0f);
    
    // FMAX.S f6, f1, f2
    uint32_t instr = encodeFPR(0b0010100, 6, 0b001, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(6);
    EXPECT_FLOAT_EQ(result, 7.25f);
}

// Test FMIN.S (Floating-Point Minimum)
TEST_F(FPInstructionTest, FMIN_S_ReturnsMinimum) {
    emulator.getCPU().setFPReg(1, 5.0f);
    emulator.getCPU().setFPReg(2, 3.0f);
    
    // FMIN.S f3, f1, f2
    uint32_t instr = encodeFPR(0b0010100, 3, 0b000, 1, 2);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, 3.0f);
}

// Test FCVT.S.W (Integer to Float Conversion - Signed)
TEST_F(FPInstructionTest, FCVT_S_W_ConvertsPositiveInt) {
    emulator.getCPU().setReg(1, 42);
    
    // FCVT.S.W f2, x1
    uint32_t instr = encodeFPR(0b1101000, 2, 0b000, 1, 0b00000);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(2);
    EXPECT_FLOAT_EQ(result, 42.0f);
}

TEST_F(FPInstructionTest, FCVT_S_W_ConvertsNegativeInt) {
    emulator.getCPU().setReg(1, static_cast<uint32_t>(-100));
    
    // FCVT.S.W f3, x1
    uint32_t instr = encodeFPR(0b1101000, 3, 0b000, 1, 0b00000);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(3);
    EXPECT_FLOAT_EQ(result, -100.0f);
}

TEST_F(FPInstructionTest, FCVT_S_W_ConvertsZero) {
    emulator.getCPU().setReg(1, 0);
    
    // FCVT.S.W f4, x1
    uint32_t instr = encodeFPR(0b1101000, 4, 0b000, 1, 0b00000);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(4);
    EXPECT_FLOAT_EQ(result, 0.0f);
}

// Test FMV.W.X (Move from Integer Register to FP Register)
TEST_F(FPInstructionTest, FMV_W_X_MovesBits) {
    // Set x1 to bit pattern of 3.14159
    uint32_t bits = floatToBits(3.14159f);
    emulator.getCPU().setReg(1, bits);
    
    // FMV.W.X f2, x1
    uint32_t instr = encodeFPR(0b1111000, 2, 0b000, 1, 0b00000);
    executeInstr(instr);
    
    float result = emulator.getCPU().getFPReg(2);
    EXPECT_FLOAT_EQ(result, 3.14159f);
}

// Test FMV.X.W (Move from FP Register to Integer Register)
TEST_F(FPInstructionTest, FMV_X_W_MovesBits) {
    float value = 2.71828f;
    emulator.getCPU().setFPReg(1, value);
    
    // FMV.X.W x2, f1
    uint32_t instr = encodeFPR(0b1110000, 2, 0b000, 1, 0b00000);
    executeInstr(instr);
    
    uint32_t result = emulator.getCPU().getReg(2);
    EXPECT_EQ(result, floatToBits(value));
}

// Test matrix multiply pattern (accumulation)
TEST_F(FPInstructionTest, MatrixMultiplyPattern) {
    // Simulate: result = 0.5 * 1.0 + 1.5 * 2.0 + 2.5 (bias)
    // Expected: 0.5 + 3.0 + 2.5 = 6.0
    
    emulator.getCPU().setFPReg(0, 2.5f);   // accumulator (bias)
    emulator.getCPU().setFPReg(1, 0.5f);   // weight 1
    emulator.getCPU().setFPReg(2, 1.0f);   // input 1
    emulator.getCPU().setFPReg(3, 1.5f);   // weight 2
    emulator.getCPU().setFPReg(4, 2.0f);   // input 2
    
    // FMUL.S f10, f1, f2  (0.5 * 1.0 = 0.5)
    executeInstr(encodeFPR(0b0001000, 10, 0b000, 1, 2));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(10), 0.5f);
    
    // FADD.S f0, f0, f10  (2.5 + 0.5 = 3.0)
    executeInstr(encodeFPR(0b0000000, 0, 0b000, 0, 10));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(0), 3.0f);
    
    // FMUL.S f11, f3, f4  (1.5 * 2.0 = 3.0)
    executeInstr(encodeFPR(0b0001000, 11, 0b000, 3, 4));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(11), 3.0f);
    
    // FADD.S f0, f0, f11  (3.0 + 3.0 = 6.0)
    executeInstr(encodeFPR(0b0000000, 0, 0b000, 0, 11));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(0), 6.0f);
}

// Test ReLU activation pattern
TEST_F(FPInstructionTest, ReLUActivationPattern) {
    // Test negative input -> 0
    emulator.getCPU().setFPReg(1, -5.5f);
    emulator.getCPU().setFPReg(2, 0.0f);
    
    // FMAX.S f3, f1, f2
    executeInstr(encodeFPR(0b0010100, 3, 0b001, 1, 2));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(3), 0.0f);
    
    // Test positive input -> input
    emulator.getCPU().setFPReg(4, 7.25f);
    emulator.getCPU().setFPReg(5, 0.0f);
    
    // FMAX.S f6, f4, f5
    executeInstr(encodeFPR(0b0010100, 6, 0b001, 4, 5));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(6), 7.25f);
}

// Test FDIV.S (Floating-Point Divide)
TEST_F(FPInstructionTest, FDIV_S_DividesFloats) {
    emulator.getCPU().setFPReg(1, 10.0f);
    emulator.getCPU().setFPReg(2, 2.0f);

    // FDIV.S f0, f1, f2  (10.0 / 2.0 = 5.0)
    executeInstr(encodeFPR(0b0001100, 0, 0b000, 1, 2));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(0), 5.0f);
}

TEST_F(FPInstructionTest, FDIV_S_FractionalResult) {
    emulator.getCPU().setFPReg(1, 1.0f);
    emulator.getCPU().setFPReg(2, 4.0f);

    // FDIV.S f0, f1, f2  (1.0 / 4.0 = 0.25)
    executeInstr(encodeFPR(0b0001100, 0, 0b000, 1, 2));
    EXPECT_FLOAT_EQ(emulator.getCPU().getFPReg(0), 0.25f);
}

// Test FEQ.S / FLT.S / FLE.S (Floating-Point Comparisons)
TEST_F(FPInstructionTest, FEQ_S_Equal) {
    emulator.getCPU().setFPReg(1, 3.0f);
    emulator.getCPU().setFPReg(2, 3.0f);

    // FEQ.S x3, f1, f2  (3.0 == 3.0 -> 1)
    executeInstr(encodeFPR(0b1010000, 3, 0b010, 1, 2));
    EXPECT_EQ(emulator.getCPU().getReg(3), 1u);
}

TEST_F(FPInstructionTest, FEQ_S_NotEqual) {
    emulator.getCPU().setFPReg(1, 3.0f);
    emulator.getCPU().setFPReg(2, 4.0f);

    // FEQ.S x1, f1, f2  (3.0 == 4.0 -> 0)
    executeInstr(encodeFPR(0b1010000, 1, 0b010, 1, 2));
    EXPECT_EQ(emulator.getCPU().getReg(1), 0u);
}

TEST_F(FPInstructionTest, FLT_S_LessThan) {
    emulator.getCPU().setFPReg(1, 2.0f);
    emulator.getCPU().setFPReg(2, 5.0f);

    // FLT.S x1, f1, f2  (2.0 < 5.0 -> 1)
    executeInstr(encodeFPR(0b1010000, 1, 0b001, 1, 2));
    EXPECT_EQ(emulator.getCPU().getReg(1), 1u);
}

TEST_F(FPInstructionTest, FLT_S_NotLessThan) {
    emulator.getCPU().setFPReg(1, 5.0f);
    emulator.getCPU().setFPReg(2, 2.0f);

    // FLT.S x1, f1, f2  (5.0 < 2.0 -> 0)
    executeInstr(encodeFPR(0b1010000, 1, 0b001, 1, 2));
    EXPECT_EQ(emulator.getCPU().getReg(1), 0u);
}

TEST_F(FPInstructionTest, FLE_S_LessOrEqual) {
    emulator.getCPU().setFPReg(1, 3.0f);
    emulator.getCPU().setFPReg(2, 3.0f);

    // FLE.S x1, f1, f2  (3.0 <= 3.0 -> 1)
    executeInstr(encodeFPR(0b1010000, 1, 0b000, 1, 2));
    EXPECT_EQ(emulator.getCPU().getReg(1), 1u);
}
