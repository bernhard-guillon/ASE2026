#include "CPU.h"

CPU::CPU() : registers_{}, pc_(0) {
    reset();
}

void CPU::validateRegister(uint8_t reg) const {
    if (reg >= NUM_REGISTERS) {
        throw std::out_of_range("Register index out of range");
    }
}

uint32_t CPU::getReg(uint8_t reg) const {
    validateRegister(reg);
    
    // x0 is hardwired to zero
    if (reg == 0) {
        return 0;
    }
    
    return registers_[reg];
}

void CPU::setReg(uint8_t reg, uint32_t value) {
    validateRegister(reg);
    
    // x0 is hardwired to zero - writes are ignored
    if (reg == 0) {
        return;
    }
    
    registers_[reg] = value;
}

void CPU::reset() {
    registers_.fill(0);
    pc_ = 0;
}

void CPU::execute(const Instruction& instr, Memory& memory) {
    switch (instr.opcode) {
        case Opcode::OP:
            executeALU(instr);
            incrementPC();
            break;
            
        case Opcode::OP_IMM:
            executeALUImmediate(instr);
            incrementPC();
            break;
            
        case Opcode::LOAD:
            executeLoad(instr, memory);
            incrementPC();
            break;
            
        case Opcode::STORE:
            executeStore(instr, memory);
            incrementPC();
            break;
            
        case Opcode::BRANCH:
            executeBranch(instr);
            break;
            
        case Opcode::JAL:
            executeJAL(instr);
            break;
            
        case Opcode::JALR:
            executeJALR(instr);
            break;
            
        case Opcode::LUI:
            executeLUI(instr);
            incrementPC();
            break;
            
        case Opcode::AUIPC:
            executeAUIPC(instr);
            incrementPC();
            break;
            
        default:
            throw std::runtime_error("Unsupported opcode in execute");
    }
}

void CPU::executeALU(const Instruction& instr) {
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t rs2_val = getReg(instr.rs2);
    uint32_t result = 0;
    
    // Decode operation based on funct3 and funct7
    switch (instr.funct3) {
        case 0b000: // ADD or SUB
            if (instr.funct7 == 0b0000000) {
                result = rs1_val + rs2_val;  // ADD
            } else if (instr.funct7 == 0b0100000) {
                result = rs1_val - rs2_val;  // SUB
            }
            break;
            
        case 0b001: // SLL (shift left logical)
            result = rs1_val << (rs2_val & 0x1F);
            break;
            
        case 0b010: // SLT (set less than, signed)
            result = (static_cast<int32_t>(rs1_val) < static_cast<int32_t>(rs2_val)) ? 1 : 0;
            break;
            
        case 0b011: // SLTU (set less than, unsigned)
            result = (rs1_val < rs2_val) ? 1 : 0;
            break;
            
        case 0b100: // XOR
            result = rs1_val ^ rs2_val;
            break;
            
        case 0b101: // SRL or SRA
            if (instr.funct7 == 0b0000000) {
                result = rs1_val >> (rs2_val & 0x1F);  // SRL (shift right logical)
            } else if (instr.funct7 == 0b0100000) {
                result = arithmeticRightShift(rs1_val, rs2_val & 0x1F);  // SRA
            }
            break;
            
        case 0b110: // OR
            result = rs1_val | rs2_val;
            break;
            
        case 0b111: // AND
            result = rs1_val & rs2_val;
            break;
    }
    
    setReg(instr.rd, result);
}

void CPU::executeALUImmediate(const Instruction& instr) {
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t result = 0;
    
    switch (instr.funct3) {
        case 0b000: // ADDI
            result = rs1_val + static_cast<uint32_t>(instr.imm);
            break;
            
        case 0b010: // SLTI (set less than immediate, signed)
            result = (static_cast<int32_t>(rs1_val) < instr.imm) ? 1 : 0;
            break;
            
        case 0b011: // SLTIU (set less than immediate, unsigned)
            result = (rs1_val < static_cast<uint32_t>(instr.imm)) ? 1 : 0;
            break;
            
        case 0b100: // XORI
            result = rs1_val ^ static_cast<uint32_t>(instr.imm);
            break;
            
        case 0b110: // ORI
            result = rs1_val | static_cast<uint32_t>(instr.imm);
            break;
            
        case 0b111: // ANDI
            result = rs1_val & static_cast<uint32_t>(instr.imm);
            break;
            
        case 0b001: // SLLI (shift left logical immediate)
            result = rs1_val << (instr.imm & 0x1F);
            break;
            
        case 0b101: // SRLI or SRAI
            if ((instr.imm & 0x400) == 0) {
                result = rs1_val >> (instr.imm & 0x1F);  // SRLI
            } else {
                result = arithmeticRightShift(rs1_val, instr.imm & 0x1F);  // SRAI
            }
            break;
    }
    
    setReg(instr.rd, result);
}

uint32_t CPU::arithmeticRightShift(uint32_t value, uint32_t shift) const {
    int32_t signed_val = static_cast<int32_t>(value);
    return static_cast<uint32_t>(signed_val >> shift);
}

void CPU::executeLoad(const Instruction& instr, Memory& memory) {
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t address = rs1_val + static_cast<uint32_t>(instr.imm);
    uint32_t value = 0;
    
    switch (instr.funct3) {
        case 0b000: // LB (load byte, sign-extended)
            {
                uint8_t byte = memory.read8(address);
                value = static_cast<uint32_t>(static_cast<int8_t>(byte));
            }
            break;
            
        case 0b001: // LH (load halfword, sign-extended)
            {
                uint16_t halfword = memory.read8(address) | 
                                   (static_cast<uint16_t>(memory.read8(address + 1)) << 8);
                value = static_cast<uint32_t>(static_cast<int16_t>(halfword));
            }
            break;
            
        case 0b010: // LW (load word)
            value = memory.read32(address);
            break;
            
        case 0b100: // LBU (load byte, unsigned)
            value = static_cast<uint32_t>(memory.read8(address));
            break;
            
        case 0b101: // LHU (load halfword, unsigned)
            value = memory.read8(address) | 
                   (static_cast<uint32_t>(memory.read8(address + 1)) << 8);
            break;
    }
    
    setReg(instr.rd, value);
}

void CPU::executeStore(const Instruction& instr, Memory& memory) {
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t rs2_val = getReg(instr.rs2);
    uint32_t address = rs1_val + static_cast<uint32_t>(instr.imm);
    
    switch (instr.funct3) {
        case 0b000: // SB (store byte)
            memory.write8(address, static_cast<uint8_t>(rs2_val & 0xFF));
            break;
            
        case 0b001: // SH (store halfword)
            memory.write8(address, static_cast<uint8_t>(rs2_val & 0xFF));
            memory.write8(address + 1, static_cast<uint8_t>((rs2_val >> 8) & 0xFF));
            break;
            
        case 0b010: // SW (store word)
            memory.write32(address, rs2_val);
            break;
    }
}

void CPU::executeBranch(const Instruction& instr) {
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t rs2_val = getReg(instr.rs2);
    bool take_branch = false;
    
    switch (instr.funct3) {
        case 0b000: // BEQ (branch if equal)
            take_branch = (rs1_val == rs2_val);
            break;
            
        case 0b001: // BNE (branch if not equal)
            take_branch = (rs1_val != rs2_val);
            break;
            
        case 0b100: // BLT (branch if less than, signed)
            take_branch = (static_cast<int32_t>(rs1_val) < static_cast<int32_t>(rs2_val));
            break;
            
        case 0b101: // BGE (branch if greater or equal, signed)
            take_branch = (static_cast<int32_t>(rs1_val) >= static_cast<int32_t>(rs2_val));
            break;
            
        case 0b110: // BLTU (branch if less than, unsigned)
            take_branch = (rs1_val < rs2_val);
            break;
            
        case 0b111: // BGEU (branch if greater or equal, unsigned)
            take_branch = (rs1_val >= rs2_val);
            break;
    }
    
    if (take_branch) {
        setPC(pc_ + static_cast<uint32_t>(instr.imm));
    } else {
        incrementPC();
    }
}

void CPU::executeJAL(const Instruction& instr) {
    // Save return address (PC + 4) in rd
    setReg(instr.rd, pc_ + 4);
    
    // Jump to PC + offset
    setPC(pc_ + static_cast<uint32_t>(instr.imm));
}

void CPU::executeJALR(const Instruction& instr) {
    uint32_t rs1_val = getReg(instr.rs1);
    
    // Calculate target: (rs1 + offset) & ~1 (clear lowest bit)
    uint32_t target = (rs1_val + static_cast<uint32_t>(instr.imm)) & ~1U;
    
    // Save return address (PC + 4) in rd
    setReg(instr.rd, pc_ + 4);
    
    // Jump to target
    setPC(target);
}

void CPU::executeLUI(const Instruction& instr) {
    // Load upper immediate into rd (lower 12 bits are zero)
    setReg(instr.rd, static_cast<uint32_t>(instr.imm));
}

void CPU::executeAUIPC(const Instruction& instr) {
    // Add upper immediate to PC
    setReg(instr.rd, pc_ + static_cast<uint32_t>(instr.imm));
}
