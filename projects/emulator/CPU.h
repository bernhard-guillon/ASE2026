#ifndef CPU_H
#define CPU_H

#include <cstdint>
#include <array>
#include <stdexcept>
#include "Instruction.h"
#include "Memory.h"

class CPU {
public:
    CPU();
    
    // Register access (x0-x31)
    uint32_t getReg(uint8_t reg) const;
    void setReg(uint8_t reg, uint32_t value);
    
    // Floating-point register access (f0-f31)
    float getFPReg(uint8_t reg) const;
    void setFPReg(uint8_t reg, float value);
    
    // Get/Set FP register as raw bits (for FMV.X.W / FMV.W.X)
    uint32_t getFPRegBits(uint8_t reg) const;
    void setFPRegBits(uint8_t reg, uint32_t bits);
    
    // Program counter
    uint32_t getPC() const { return pc_; }
    void setPC(uint32_t value) { pc_ = value; }
    void incrementPC() { pc_ += 4; }
    
    // Reset CPU state
    void reset();
    
    // Execute single instruction
    void execute(const Instruction& instr, Memory& memory);
    
    static constexpr uint8_t NUM_REGISTERS = 32;
    static constexpr uint8_t NUM_FP_REGISTERS = 32;
    
private:
    std::array<uint32_t, NUM_REGISTERS> registers_;
    std::array<float, NUM_FP_REGISTERS> fp_registers_;
    uint32_t pc_;
    
    void validateRegister(uint8_t reg) const;
    void validateFPRegister(uint8_t reg) const;
    
    // ALU operations
    void executeALU(const Instruction& instr);
    void executeALUImmediate(const Instruction& instr);
    
    // Memory operations
    void executeLoad(const Instruction& instr, Memory& memory);
    void executeStore(const Instruction& instr, Memory& memory);
    
    // Branch operations
    void executeBranch(const Instruction& instr);
    
    // Jump operations
    void executeJAL(const Instruction& instr);
    void executeJALR(const Instruction& instr);
    
    // Upper immediate operations
    void executeLUI(const Instruction& instr);
    void executeAUIPC(const Instruction& instr);
    
    // Floating-point operations (F extension)
    void executeFPLoad(const Instruction& instr, Memory& memory);
    void executeFPStore(const Instruction& instr, Memory& memory);
    void executeFPArithmetic(const Instruction& instr);
    
    // Helper for arithmetic right shift
    uint32_t arithmeticRightShift(uint32_t value, uint32_t shift) const;
};

#endif // CPU_H
