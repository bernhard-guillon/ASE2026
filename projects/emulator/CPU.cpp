#include "CPU.h"
#include <cstring>  // for memcpy

CPU::CPU() : registers_{}, fp_registers_{}, pc_(0) {
    reset();
}

void CPU::validateRegister(uint8_t reg) const {
    if (reg >= NUM_REGISTERS) {
        throw std::out_of_range("Register index out of range");
    }
}

void CPU::validateFPRegister(uint8_t reg) const {
    if (reg >= NUM_FP_REGISTERS) {
        throw std::out_of_range("FP register index out of range");
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

float CPU::getFPReg(uint8_t reg) const {
    validateFPRegister(reg);
    return fp_registers_[reg];
}

void CPU::setFPReg(uint8_t reg, float value) {
    validateFPRegister(reg);
    fp_registers_[reg] = value;
}

uint32_t CPU::getFPRegBits(uint8_t reg) const {
    validateFPRegister(reg);
    uint32_t bits;
    std::memcpy(&bits, &fp_registers_[reg], sizeof(uint32_t));
    return bits;
}

void CPU::setFPRegBits(uint8_t reg, uint32_t bits) {
    validateFPRegister(reg);
    std::memcpy(&fp_registers_[reg], &bits, sizeof(uint32_t));
}

void CPU::reset() {
    registers_.fill(0);
    fp_registers_.fill(0.0f);
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
            
        case Opcode::LOAD_FP:
            executeFPLoad(instr, memory);
            incrementPC();
            break;
            
        case Opcode::STORE_FP:
            executeFPStore(instr, memory);
            incrementPC();
            break;
            
        case Opcode::OP_FP:
            executeFPArithmetic(instr);
            incrementPC();
            break;

        case Opcode::CUSTOM0:
        case Opcode::CUSTOM3:
            executeNeural(instr, memory);
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

// F Extension: Floating-Point Load
void CPU::executeFPLoad(const Instruction& instr, Memory& memory) {
    // FLW: Load 32-bit float from memory
    // Only supports funct3 = 0b010 (FLW)
    if (instr.funct3 != 0b010) {
        throw std::runtime_error("Unsupported FP load funct3");
    }
    
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t address = rs1_val + static_cast<uint32_t>(instr.imm);
    
    // Load 32-bit value from memory
    uint32_t value = memory.read32(address);
    
    // Store as FP register bits
    setFPRegBits(instr.rd, value);
}

// F Extension: Floating-Point Store
void CPU::executeFPStore(const Instruction& instr, Memory& memory) {
    // FSW: Store 32-bit float to memory
    // Only supports funct3 = 0b010 (FSW)
    if (instr.funct3 != 0b010) {
        throw std::runtime_error("Unsupported FP store funct3");
    }
    
    uint32_t rs1_val = getReg(instr.rs1);
    uint32_t address = rs1_val + static_cast<uint32_t>(instr.imm);
    
    // Get FP register as bits
    uint32_t value = getFPRegBits(instr.rs2);
    
    // Store to memory
    memory.write32(address, value);
}

// F Extension: Floating-Point Arithmetic
void CPU::executeFPArithmetic(const Instruction& instr) {
    // Dispatch based on funct7
    switch (instr.funct7) {
        case 0b0000000: {  // FADD.S
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            setFPReg(instr.rd, rs1_val + rs2_val);
            break;
        }
        case 0b0000100: {  // FSUB.S
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            setFPReg(instr.rd, rs1_val - rs2_val);
            break;
        }
        case 0b0001000: {  // FMUL.S
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            setFPReg(instr.rd, rs1_val * rs2_val);
            break;
        }
        case 0b0001100: {  // FDIV.S
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            setFPReg(instr.rd, rs1_val / rs2_val);
            break;
        }
        case 0b1010000: {  // FEQ.S / FLT.S / FLE.S (float comparisons, result in integer register)
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            uint32_t cmp_result = 0;
            if (instr.funct3 == 0b010) {        // FEQ.S
                cmp_result = (rs1_val == rs2_val) ? 1 : 0;
            } else if (instr.funct3 == 0b001) { // FLT.S
                cmp_result = (rs1_val < rs2_val) ? 1 : 0;
            } else if (instr.funct3 == 0b000) { // FLE.S
                cmp_result = (rs1_val <= rs2_val) ? 1 : 0;
            } else {
                throw std::runtime_error("Unsupported FP comparison funct3");
            }
            setReg(instr.rd, cmp_result);
            break;
        }
        case 0b0010100: {  // FMAX.S / FMIN.S (based on funct3)
            float rs1_val = getFPReg(instr.rs1);
            float rs2_val = getFPReg(instr.rs2);
            if (instr.funct3 == 0b001) {  // FMAX.S
                setFPReg(instr.rd, (rs1_val > rs2_val) ? rs1_val : rs2_val);
            } else if (instr.funct3 == 0b000) {  // FMIN.S
                setFPReg(instr.rd, (rs1_val < rs2_val) ? rs1_val : rs2_val);
            } else {
                throw std::runtime_error("Unsupported FMIN/FMAX funct3");
            }
            break;
        }
        case 0b1101000: {  // FCVT.S.W / FCVT.S.WU (int to float conversion)
            if (instr.rs2 == 0b00000) {  // FCVT.S.W (signed int to float)
                int32_t int_val = static_cast<int32_t>(getReg(instr.rs1));
                setFPReg(instr.rd, static_cast<float>(int_val));
            } else if (instr.rs2 == 0b00001) {  // FCVT.S.WU (unsigned int to float)
                uint32_t uint_val = getReg(instr.rs1);
                setFPReg(instr.rd, static_cast<float>(uint_val));
            } else {
                throw std::runtime_error("Unsupported FCVT.S.W rs2");
            }
            break;
        }
        case 0b1110000: {  // FMV.X.W / FCLASS.S
            if (instr.funct3 == 0b000 && instr.rs2 == 0b00000) {  // FMV.X.W
                // Move bits from FP register to integer register
                uint32_t bits = getFPRegBits(instr.rs1);
                setReg(instr.rd, bits);
            } else if (instr.funct3 == 0b001 && instr.rs2 == 0b00000) {  // FCLASS.S
                throw std::runtime_error("FCLASS.S not yet implemented");
            } else {
                throw std::runtime_error("Unsupported funct7=0b1110000 operation");
            }
            break;
        }
        case 0b1100000: {  // FCVT.W.S / FCVT.WU.S (float to int conversion)
            if (instr.rs2 == 0b00000) {  // FCVT.W.S (float to signed int)
                float fp_val = getFPReg(instr.rs1);
                setReg(instr.rd, static_cast<uint32_t>(static_cast<int32_t>(fp_val)));
            } else if (instr.rs2 == 0b00001) {  // FCVT.WU.S (float to unsigned int)
                float fp_val = getFPReg(instr.rs1);
                setReg(instr.rd, static_cast<uint32_t>(fp_val));
            } else {
                throw std::runtime_error("Unsupported FCVT.W.S rs2");
            }
            break;
        }
        case 0b0010000: {  // FSGNJ.S / FSGNJN.S / FSGNJX.S (sign injection)
            uint32_t rs1_bits = getFPRegBits(instr.rs1);
            uint32_t rs2_bits = getFPRegBits(instr.rs2);
            uint32_t result_bits;
            
            if (instr.funct3 == 0b000) {  // FSGNJ.S
                // Copy sign bit from rs2 to rs1 magnitude
                result_bits = (rs2_bits & 0x80000000) | (rs1_bits & 0x7FFFFFFF);
            } else if (instr.funct3 == 0b001) {  // FSGNJN.S
                // Copy negated sign bit from rs2 to rs1 magnitude
                result_bits = ((rs2_bits ^ 0x80000000) & 0x80000000) | (rs1_bits & 0x7FFFFFFF);
            } else if (instr.funct3 == 0b010) {  // FSGNJX.S
                // XOR sign bits from rs1 and rs2
                result_bits = ((rs1_bits ^ rs2_bits) & 0x80000000) | (rs1_bits & 0x7FFFFFFF);
            } else {
                throw std::runtime_error("Unsupported FSGNJ funct3");
            }
            setFPRegBits(instr.rd, result_bits);
            break;
        }
        case 0b1111000: {  // FMV.W.X
            if (instr.funct3 == 0b000 && instr.rs2 == 0b00000) {  // FMV.W.X
                // Move bits from integer register to FP register
                uint32_t bits = getReg(instr.rs1);
                setFPRegBits(instr.rd, bits);
            } else {
                throw std::runtime_error("Unsupported funct7=0b1111000 operation");
            }
            break;
        }
        default:
            throw std::runtime_error("Unsupported FP arithmetic funct7");
    }
}

void CPU::executeNeural(const Instruction& instr, Memory& memory) {
    auto& raw_mem = memory.bytesMutable();
    uint32_t status = NeuralOps::ERR_INVALID_PTR;
    const bool is_v2 = (instr.opcode == Opcode::CUSTOM3);

    switch (instr.neural_op) {
        case 0: // NMATVEC.F32 rd_status, rs_desc
            status = is_v2
                ? NeuralOps::matvec_f32_v2(raw_mem, getReg(instr.rs1))
                : NeuralOps::matvec_f32(raw_mem, getReg(instr.rs1));
            break;
        case 4: // NMATVEC4X.F32 rd_status, rs_desc (CUSTOM3 only)
            if (!is_v2) {
                throw std::runtime_error("Unsupported neural custom operation");
            }
            status = NeuralOps::matvec_f32_v2_lane4(raw_mem, getReg(instr.rs1));
            break;
        case 5: // NMATVEC8X.F32 rd_status, rs_desc (CUSTOM3 only)
            if (!is_v2) {
                throw std::runtime_error("Unsupported neural custom operation");
            }
            status = NeuralOps::matvec_f32_v2_lane8(raw_mem, getReg(instr.rs1));
            break;
        case 6: // NMATVEC8XP.F32 rd_status, rs_desc (CUSTOM3 only)
            if (!is_v2) {
                throw std::runtime_error("Unsupported neural custom operation");
            }
            // C++ oracle keeps semantics identical to lane8; PMAC is RTL-only speed path.
            status = NeuralOps::matvec_f32_v2_lane8(raw_mem, getReg(instr.rs1));
            break;
        case 7: // NMATVEC8XP2.F32 rd_status, rs_desc (CUSTOM3 only)
            if (!is_v2) {
                throw std::runtime_error("Unsupported neural custom operation");
            }
            // C++ oracle keeps semantics identical to lane8; PMAC2 is RTL-only speed path.
            status = NeuralOps::matvec_f32_v2_lane8(raw_mem, getReg(instr.rs1));
            break;
        case 1: // NVRELU.F32 rd_status, rs_dst, rs_src, rs_len
            status = is_v2
                ? NeuralOps::vec_relu_f32_v2(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                )
                : NeuralOps::vec_relu_f32(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                );
            break;
        case 2: // NVSIGPWL.F32 rd_status, rs_dst, rs_src, rs_len
            status = is_v2
                ? NeuralOps::vec_sigmoid_pwl_f32_v2(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                )
                : NeuralOps::vec_sigmoid_pwl_f32(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                );
            break;
        case 3: // NVCLAMPU8.F32 rd_status, rs_dst_u8, rs_src_f32, rs_len
            status = is_v2
                ? NeuralOps::vec_clamp_scale_u8_f32_v2(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                )
                : NeuralOps::vec_clamp_scale_u8_f32(
                    raw_mem,
                    getReg(instr.rs1),
                    getReg(instr.rs2),
                    getReg(instr.rs3)
                );
            break;
        default:
            throw std::runtime_error("Unsupported neural custom operation");
    }

    setReg(instr.rd, status);
}
