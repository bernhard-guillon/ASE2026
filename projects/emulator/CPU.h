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
    
    // Program counter
    uint32_t getPC() const { return pc_; }
    void setPC(uint32_t value) { pc_ = value; }
    void incrementPC() { pc_ += 4; }
    
    // Reset CPU state
    void reset();
    
    // Execute single instruction
    void execute(const Instruction& instr, Memory& memory);
    
    static constexpr uint8_t NUM_REGISTERS = 32;
    
private:
    std::array<uint32_t, NUM_REGISTERS> registers_;
    uint32_t pc_;
    
    void validateRegister(uint8_t reg) const;
    
    // ALU operations
    void executeALU(const Instruction& instr);
    void executeALUImmediate(const Instruction& instr);
    
    // Helper for arithmetic right shift
    uint32_t arithmeticRightShift(uint32_t value, uint32_t shift) const;
};

#endif // CPU_H
