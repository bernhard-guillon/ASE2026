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
