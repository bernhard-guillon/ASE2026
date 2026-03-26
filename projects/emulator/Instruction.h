#ifndef INSTRUCTION_H
#define INSTRUCTION_H

#include <cstdint>

// RV32I instruction formats
enum class InstructionFormat {
    R_TYPE,  // Register-register operations
    I_TYPE,  // Immediate and load operations
    S_TYPE,  // Store operations
    B_TYPE,  // Branch operations
    U_TYPE,  // Upper immediate operations
    J_TYPE,  // Jump operations
    N_TYPE,  // Neural custom operations
    UNKNOWN
};

// Opcodes for RV32I and F extension
enum class Opcode : uint8_t {
    LOAD      = 0b0000011,
    LOAD_FP   = 0b0000111,  // F extension: FLW
    OP_IMM    = 0b0010011,
    AUIPC     = 0b0010111,
    STORE     = 0b0100011,
    STORE_FP  = 0b0100111,  // F extension: FSW
    OP        = 0b0110011,
    OP_FP     = 0b1010011,  // F extension: FADD.S, FMUL.S, etc.
    CUSTOM0   = 0b1110111,  // Neural custom extension
    LUI       = 0b0110111,
    BRANCH    = 0b1100011,
    JALR      = 0b1100111,
    JAL       = 0b1101111,
    SYSTEM    = 0b1110011,
    UNKNOWN   = 0xFF
};

struct Instruction {
    uint32_t raw;           // Original 32-bit instruction
    InstructionFormat format;
    Opcode opcode;
    
    // Common fields
    uint8_t rd;             // Destination register (bits 7-11)
    uint8_t rs1;            // Source register 1 (bits 15-19)
    uint8_t rs2;            // Source register 2 (bits 20-24)
    uint8_t funct3;         // Function code 3 bits (bits 12-14)
    uint8_t funct7;         // Function code 7 bits (bits 25-31)
    uint8_t rs3;            // Neural/custom source register 3
    uint8_t neural_op;      // Neural operation id (bits 31:27 for CUSTOM0)
    
    // Immediate values (sign-extended)
    int32_t imm;            // Decoded immediate value
    
    Instruction() : raw(0), format(InstructionFormat::UNKNOWN), 
                    opcode(Opcode::UNKNOWN), rd(0), rs1(0), rs2(0),
                    funct3(0), funct7(0), rs3(0), neural_op(0), imm(0) {}
};

class InstructionDecoder {
public:
    static Instruction decode(uint32_t instruction);
    
private:
    static Opcode extractOpcode(uint32_t instruction);
    static InstructionFormat determineFormat(Opcode opcode);
    
    // Field extraction
    static uint8_t extractRd(uint32_t instruction);
    static uint8_t extractRs1(uint32_t instruction);
    static uint8_t extractRs2(uint32_t instruction);
    static uint8_t extractFunct3(uint32_t instruction);
    static uint8_t extractFunct7(uint32_t instruction);
    
    // Immediate decoding (sign-extended)
    static int32_t decodeImmI(uint32_t instruction);
    static int32_t decodeImmS(uint32_t instruction);
    static int32_t decodeImmB(uint32_t instruction);
    static int32_t decodeImmU(uint32_t instruction);
    static int32_t decodeImmJ(uint32_t instruction);
    
    // Sign extension helper
    static int32_t signExtend(uint32_t value, uint8_t bits);
};

#endif // INSTRUCTION_H
