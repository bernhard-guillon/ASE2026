#ifndef EMULATOR_H
#define EMULATOR_H

#include <cstdint>
#include <string>
#include <vector>
#include "CPU.h"
#include "Memory.h"
#include "Instruction.h"

class Emulator {
public:
    Emulator(size_t memory_size = 65536);
    
    // Load program into memory starting at address
    void loadProgram(const std::vector<uint32_t>& program, uint32_t start_address = 0);
    
    // Run until halt or max instructions
    void run(uint32_t max_instructions = 10000);
    
    // Execute single step
    void step();
    
    // Get CPU and memory for inspection
    CPU& getCPU() { return cpu_; }
    Memory& getMemory() { return memory_; }
    
    // Check if halted
    bool isHalted() const { return halted_; }
    
    // Get exit code (set by exit syscall)
    int getExitCode() const { return exit_code_; }
    
    // Reset emulator state
    void reset();
    
private:
    CPU cpu_;
    Memory memory_;
    bool halted_;
    int exit_code_;
    
    void handleSystemCall();
};

#endif // EMULATOR_H
