#include "Emulator.h"
#include <iostream>
#include <stdexcept>

Emulator::Emulator(size_t memory_size) 
    : cpu_(), memory_(memory_size), halted_(false) {
}

void Emulator::loadProgram(const std::vector<uint32_t>& program, uint32_t start_address) {
    if (start_address + program.size() * 4 > memory_.size()) {
        throw std::out_of_range("Program too large for memory");
    }
    
    uint32_t address = start_address;
    for (uint32_t instruction : program) {
        memory_.write32(address, instruction);
        address += 4;
    }
    
    cpu_.setPC(start_address);
}

void Emulator::run(uint32_t max_instructions) {
    for (uint32_t i = 0; i < max_instructions && !halted_; ++i) {
        step();
    }
}

void Emulator::step() {
    if (halted_) {
        return;
    }
    
    uint32_t pc = cpu_.getPC();
    
    // Check PC bounds
    if (pc + 4 > memory_.size()) {
        throw std::runtime_error("PC out of bounds");
    }
    
    // Fetch instruction
    uint32_t instruction_word = memory_.read32(pc);
    
    // Decode instruction
    Instruction instr = InstructionDecoder::decode(instruction_word);
    
    // Handle ECALL specially
    if (instr.opcode == Opcode::SYSTEM) {
        if (instr.funct3 == 0b000 && instr.imm == 0) {
            handleSystemCall();
            return;
        }
        // EBREAK or other SYSTEM instructions
        throw std::runtime_error("Unsupported SYSTEM instruction");
    }
    
    // Execute instruction
    cpu_.execute(instr, memory_);
}

void Emulator::handleSystemCall() {
    // Syscall number in a7 (x17)
    uint32_t syscall_num = cpu_.getReg(17);
    
    switch (syscall_num) {
        case 64: { // write(fd, buf, count)
            uint32_t fd = cpu_.getReg(10);      // a0
            uint32_t buf = cpu_.getReg(11);     // a1
            uint32_t count = cpu_.getReg(12);   // a2
            
            if (fd == 1 || fd == 2) {  // stdout or stderr
                for (uint32_t i = 0; i < count; ++i) {
                    char c = static_cast<char>(memory_.read8(buf + i));
                    std::cout << c;
                }
                std::cout.flush();
                
                // Return bytes written in a0
                cpu_.setReg(10, count);
            } else {
                // Unsupported fd, return error
                cpu_.setReg(10, static_cast<uint32_t>(-1));
            }
            
            cpu_.incrementPC();
            break;
        }
        
        case 93: { // exit(status)
            halted_ = true;
            // Exit code is in a0 (x10), but we just halt
            break;
        }
        
        default:
            throw std::runtime_error("Unsupported syscall: " + std::to_string(syscall_num));
    }
}

void Emulator::reset() {
    cpu_.reset();
    memory_.reset();
    halted_ = false;
}
