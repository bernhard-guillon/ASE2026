#ifndef EMULATOR_H
#define EMULATOR_H

#include <cstdint>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include "CPU.h"
#include "Memory.h"
#include "Instruction.h"

class Emulator {
public:
    Emulator(size_t memory_size = 1024 * 1024 * 1024);  // 1GB default for mmap support
    
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
    
    // Get current heap break
    uint32_t getHeapBreak() const { return heap_break_; }
    
    // Reset emulator state
    void reset();
    
private:
    CPU cpu_;
    Memory memory_;
    bool halted_;
    int exit_code_;
    uint32_t heap_break_;  // Current heap break for brk syscall
    
    // mmap tracking: address -> size
    std::map<uint32_t, uint32_t> mmap_regions_;
    uint32_t mmap_base_;  // Next available mmap address
    
    // File descriptor tracking: fd -> FILE*
    std::map<int, std::fstream*> open_files_;
    int next_fd_;  // Next file descriptor to assign (starts at 3 after stdin/stdout/stderr)
    
    // File position tracking: fd -> offset
    std::map<int, uint32_t> file_positions_;
    
    void handleSystemCall();
};

#endif // EMULATOR_H
