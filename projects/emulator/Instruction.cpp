#include "Instruction.h"

Instruction InstructionDecoder::decode(uint32_t instruction) {
    Instruction instr;
    instr.raw = instruction;
    
    // Extract opcode and determine format
    instr.opcode = extractOpcode(instruction);
    instr.format = determineFormat(instr.opcode);
    
    // Extract common fields
    instr.rd = extractRd(instruction);
    instr.rs1 = extractRs1(instruction);
    instr.rs2 = extractRs2(instruction);
    instr.funct3 = extractFunct3(instruction);
    instr.funct7 = extractFunct7(instruction);
    
    // Decode immediate based on format
    switch (instr.format) {
        case InstructionFormat::I_TYPE:
            instr.imm = decodeImmI(instruction);
            break;
        case InstructionFormat::S_TYPE:
            instr.imm = decodeImmS(instruction);
            break;
        case InstructionFormat::B_TYPE:
            instr.imm = decodeImmB(instruction);
            break;
        case InstructionFormat::U_TYPE:
            instr.imm = decodeImmU(instruction);
            break;
        case InstructionFormat::J_TYPE:
            instr.imm = decodeImmJ(instruction);
            break;
        default:
            instr.imm = 0;
            break;
    }
    
    return instr;
}

Opcode InstructionDecoder::extractOpcode(uint32_t instruction) {
    uint8_t opcode = instruction & 0b1111111;
    
    switch (opcode) {
        case 0b0000011: return Opcode::LOAD;
        case 0b0000111: return Opcode::LOAD_FP;
        case 0b0010011: return Opcode::OP_IMM;
        case 0b0010111: return Opcode::AUIPC;
        case 0b0100011: return Opcode::STORE;
        case 0b0100111: return Opcode::STORE_FP;
        case 0b0110011: return Opcode::OP;
        case 0b1010011: return Opcode::OP_FP;
        case 0b0110111: return Opcode::LUI;
        case 0b1100011: return Opcode::BRANCH;
        case 0b1100111: return Opcode::JALR;
        case 0b1101111: return Opcode::JAL;
        case 0b1110011: return Opcode::SYSTEM;
        default:        return Opcode::UNKNOWN;
    }
}

InstructionFormat InstructionDecoder::determineFormat(Opcode opcode) {
    switch (opcode) {
        case Opcode::OP:
        case Opcode::OP_FP:
            return InstructionFormat::R_TYPE;
        case Opcode::OP_IMM:
        case Opcode::LOAD:
        case Opcode::LOAD_FP:
        case Opcode::JALR:
        case Opcode::SYSTEM:
            return InstructionFormat::I_TYPE;
        case Opcode::STORE:
        case Opcode::STORE_FP:
            return InstructionFormat::S_TYPE;
        case Opcode::BRANCH:
            return InstructionFormat::B_TYPE;
        case Opcode::LUI:
        case Opcode::AUIPC:
            return InstructionFormat::U_TYPE;
        case Opcode::JAL:
            return InstructionFormat::J_TYPE;
        default:
            return InstructionFormat::UNKNOWN;
    }
}

uint8_t InstructionDecoder::extractRd(uint32_t instruction) {
    return (instruction >> 7) & 0b11111;
}

uint8_t InstructionDecoder::extractRs1(uint32_t instruction) {
    return (instruction >> 15) & 0b11111;
}

uint8_t InstructionDecoder::extractRs2(uint32_t instruction) {
    return (instruction >> 20) & 0b11111;
}

uint8_t InstructionDecoder::extractFunct3(uint32_t instruction) {
    return (instruction >> 12) & 0b111;
}

uint8_t InstructionDecoder::extractFunct7(uint32_t instruction) {
    return (instruction >> 25) & 0b1111111;
}

int32_t InstructionDecoder::decodeImmI(uint32_t instruction) {
    // I-type: imm[11:0] = inst[31:20]
    uint32_t imm = (instruction >> 20) & 0xFFF;
    return signExtend(imm, 12);
}

int32_t InstructionDecoder::decodeImmS(uint32_t instruction) {
    // S-type: imm[11:5] = inst[31:25], imm[4:0] = inst[11:7]
    uint32_t imm_11_5 = (instruction >> 25) & 0b1111111;
    uint32_t imm_4_0 = (instruction >> 7) & 0b11111;
    uint32_t imm = (imm_11_5 << 5) | imm_4_0;
    return signExtend(imm, 12);
}

int32_t InstructionDecoder::decodeImmB(uint32_t instruction) {
    // B-type: imm[12|10:5|4:1|11] from inst[31|30:25|11:8|7]
    uint32_t imm_12 = (instruction >> 31) & 0b1;
    uint32_t imm_11 = (instruction >> 7) & 0b1;
    uint32_t imm_10_5 = (instruction >> 25) & 0b111111;
    uint32_t imm_4_1 = (instruction >> 8) & 0b1111;
    
    uint32_t imm = (imm_12 << 12) | (imm_11 << 11) | (imm_10_5 << 5) | (imm_4_1 << 1);
    return signExtend(imm, 13);
}

int32_t InstructionDecoder::decodeImmU(uint32_t instruction) {
    // U-type: imm[31:12] = inst[31:12]
    return static_cast<int32_t>(instruction & 0xFFFFF000);
}

int32_t InstructionDecoder::decodeImmJ(uint32_t instruction) {
    // J-type: imm[20|10:1|11|19:12] from inst[31|30:21|20|19:12]
    uint32_t imm_20 = (instruction >> 31) & 0b1;
    uint32_t imm_19_12 = (instruction >> 12) & 0xFF;
    uint32_t imm_11 = (instruction >> 20) & 0b1;
    uint32_t imm_10_1 = (instruction >> 21) & 0b1111111111;
    
    uint32_t imm = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1);
    return signExtend(imm, 21);
}

int32_t InstructionDecoder::signExtend(uint32_t value, uint8_t bits) {
    // Check if sign bit is set
    uint32_t sign_bit = 1U << (bits - 1);
    if (value & sign_bit) {
        // Sign extend by setting all upper bits to 1
        uint32_t mask = ~((1U << bits) - 1);
        return static_cast<int32_t>(value | mask);
    }
    return static_cast<int32_t>(value);
}
