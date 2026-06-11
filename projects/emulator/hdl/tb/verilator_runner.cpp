// Verilator C++ Testbench for RISC-V Emulator
// Provides same interface as emulator_runner

#include <verilated.h>
#include "Vemulator_top.h"

#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <iomanip>
#include <string>
#include <unordered_map>
#include <limits>
#include <termios.h>
#include <unistd.h>
#include <sys/select.h>
#include <csignal>

// DPI-C functions for FPU operations (IEEE 754 single-precision)
extern "C" {
    uint32_t fp_add(uint32_t a, uint32_t b) {
        float fa, fb, fr;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        fr = fa + fb;
        uint32_t result;
        memcpy(&result, &fr, sizeof(uint32_t));
        return result;
    }
    
    uint32_t fp_sub(uint32_t a, uint32_t b) {
        float fa, fb, fr;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        fr = fa - fb;
        uint32_t result;
        memcpy(&result, &fr, sizeof(uint32_t));
        return result;
    }
    
    uint32_t fp_mul(uint32_t a, uint32_t b) {
        float fa, fb, fr;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        fr = fa * fb;
        uint32_t result;
        memcpy(&result, &fr, sizeof(uint32_t));
        return result;
    }
    
    uint32_t fp_div(uint32_t a, uint32_t b) {
        float fa, fb, fr;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        fr = fa / fb;
        uint32_t result;
        memcpy(&result, &fr, sizeof(uint32_t));
        return result;
    }
    
    uint32_t fp_cmp_lt(uint32_t a, uint32_t b) {
        float fa, fb;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        return fa < fb ? 1 : 0;
    }
    
    uint32_t fp_cmp_le(uint32_t a, uint32_t b) {
        float fa, fb;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        return fa <= fb ? 1 : 0;
    }
    
    uint32_t fp_cmp_eq(uint32_t a, uint32_t b) {
        float fa, fb;
        memcpy(&fa, &a, sizeof(float));
        memcpy(&fb, &b, sizeof(float));
        return fa == fb ? 1 : 0;
    }
    
    uint32_t fp_cvt_w_s(uint32_t a) {
        float fa;
        memcpy(&fa, &a, sizeof(float));
        int32_t result = static_cast<int32_t>(fa);
        return static_cast<uint32_t>(result);
    }
    
    uint32_t fp_cvt_s_w(int32_t a) {
        float fr = static_cast<float>(a);
        uint32_t result;
        memcpy(&result, &fr, sizeof(uint32_t));
        return result;
    }
}

// ELF header structures (simplified)
struct Elf32_Ehdr {
    uint8_t  e_ident[16];
    uint16_t e_type;
    uint16_t e_machine;
    uint32_t e_version;
    uint32_t e_entry;
    uint32_t e_phoff;
    uint32_t e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize;
    uint16_t e_phentsize;
    uint16_t e_phnum;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
};

struct Elf32_Phdr {
    uint32_t p_type;
    uint32_t p_offset;
    uint32_t p_vaddr;
    uint32_t p_paddr;
    uint32_t p_filesz;
    uint32_t p_memsz;
    uint32_t p_flags;
    uint32_t p_align;
};

constexpr uint32_t PT_LOAD = 1;
constexpr uint32_t FRAMEBUFFER_ADDR = 0x20000;
constexpr uint32_t FRAMEBUFFER_SIZE = 400;
constexpr uint32_t FRAMEBUFFER_STRIDE = 320;
constexpr uint32_t MEM_SIZE = 0x200000;  // Keep in sync with emulator_top default

#include <verilated_vcd_c.h>

class VerilatorRunner {
public:
    VerilatorRunner() : top_(new Vemulator_top), time_(0), trace_(nullptr) {
        top_->clk = 0;
        top_->rst_n = 0;
        top_->start = 0;
        top_->reg_write_en = 0;
        top_->force_a0_en = 0;
        top_->force_a0_data = 0;
        top_->mem_init_en = 0;
        top_->pause = 0;
    }
    
    ~VerilatorRunner() {
        for (auto& pair : open_files_) {
            pair.second->close();
            delete pair.second;
        }
        open_files_.clear();
        file_positions_.clear();

        if (trace_) {
            trace_->close();
            delete trace_;
        }
        delete top_;
    }
    
    void enableTrace(const char* filename) {
        Verilated::traceEverOn(true);
        trace_ = new VerilatedVcdC;
        top_->trace(trace_, 99);
        trace_->open(filename);
    }
    
    void reset() {
        top_->rst_n = 0;
        for (int i = 0; i < 4; ++i) {
            tick();
        }
        top_->rst_n = 1;
        tick();
    }
    
    void tick() {
        top_->clk = 0;
        top_->eval();
        if (trace_) trace_->dump(time_);
        time_++;
        
        top_->clk = 1;
        top_->eval();
        if (trace_) trace_->dump(time_);
        time_++;
    }
    
    bool loadElf(const std::vector<uint8_t>& data, uint32_t& entry_point) {
        // Validate ELF magic
        if (data.size() < sizeof(Elf32_Ehdr) ||
            data[0] != 0x7F || data[1] != 'E' || data[2] != 'L' || data[3] != 'F') {
            return false;
        }
        
        const Elf32_Ehdr* ehdr = reinterpret_cast<const Elf32_Ehdr*>(data.data());
        entry_point = ehdr->e_entry;
        
        // Load program headers
        for (int i = 0; i < ehdr->e_phnum; ++i) {
            size_t phdr_offset = ehdr->e_phoff + i * ehdr->e_phentsize;
            if (phdr_offset + sizeof(Elf32_Phdr) > data.size()) break;
            
            const Elf32_Phdr* phdr = reinterpret_cast<const Elf32_Phdr*>(data.data() + phdr_offset);
            
            if (phdr->p_type == PT_LOAD) {
                // Load segment data
                for (uint32_t j = 0; j < phdr->p_filesz && phdr->p_offset + j < data.size(); ++j) {
                    writeMem(phdr->p_vaddr + j, data[phdr->p_offset + j]);
                }
                // Zero-fill BSS
                for (uint32_t j = phdr->p_filesz; j < phdr->p_memsz; ++j) {
                    writeMem(phdr->p_vaddr + j, 0);
                }
            }
        }
        
        return true;
    }
    
    void loadRaw(const std::vector<uint8_t>& data) {
        for (size_t i = 0; i < data.size(); ++i) {
            writeMem(i, data[i]);
        }
    }
    
    void writeMem(uint32_t addr, uint8_t value) {
        top_->mem_init_en = 1;
        top_->mem_init_addr = addr;
        top_->mem_init_data = value;
        tick();
        top_->mem_init_en = 0;
    }
    
    uint8_t readMem(uint32_t addr) {
        top_->mem_read_addr = addr;
        top_->eval();
        return top_->mem_read_data;
    }

    uint32_t readMemWord(uint32_t addr) {
        uint32_t b0 = readMem(addr);
        uint32_t b1 = readMem(addr + 1);
        uint32_t b2 = readMem(addr + 2);
        uint32_t b3 = readMem(addr + 3);
        return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
    }
    
    void setReg(uint8_t reg, uint32_t value) {
        top_->reg_write_en = 1;
        top_->reg_write_addr = reg;
        top_->reg_write_data = value;
        tick();
        top_->reg_write_en = 0;
    }
    
    void setPC(uint32_t pc) {
        top_->pc_init_en = 1;
        top_->pc_init_addr = pc;
        tick();
        top_->pc_init_en = 0;
    }
    
    void start() {
        top_->start = 1;
        tick();
        top_->start = 0;
    }
    
    void setPause(bool paused) {
        top_->pause = paused;
    }
    
    bool run(uint32_t max_cycles, bool hold_char = false, uint32_t char_code = 0, bool debug_output = false) {
        // Handle syscalls in testbench
        top_->syscall_done = 0;
        top_->syscall_ret = 0;
        syscall_error_ = false;
        syscall_error_num_ = 0;
        // Pulse force_a0 for first N cycles — long enough for MODEL_MAP_INPUT
        // to read a0 via "mv %0, a0", short enough to avoid corrupting neural
        // ops that reuse a0 as scratch during run_forward_pass().
        // force_a0 writes regs[10] every cycle when enabled (RTL line 396-398).
        const uint32_t FORCE_A0_PULSE = hold_char ? 100 : 0;
        top_->force_a0_en = hold_char ? 1 : 0;
        top_->force_a0_data = char_code;
        
        // PC trace ring buffer and hang detection
        uint32_t pc_trace[128];
        uint32_t pc_trace_idx = 0;
        uint32_t prev_pc = 0xFFFFFFFF;
        uint32_t stall_cycles = 0;
        const uint32_t STALL_THRESHOLD = 1000000;  // 1M cycles without PC change = hang (neural ops can take many cycles)
        uint32_t final_cycle_count = 0;
        uint32_t iteration_count = 0;
        uint32_t i;
        
        for (i = 0; i < max_cycles && !top_->halted && !syscall_error_; ++i) {
            final_cycle_count = i;
            // Release force_a0 after pulse duration
            if (FORCE_A0_PULSE > 0 && i == FORCE_A0_PULSE) {
                top_->force_a0_en = 0;
            }
            uint32_t cur_pc = getDebugPc();
            pc_trace[pc_trace_idx % 128] = cur_pc;
            pc_trace_idx++;
            
            // Hang detection: check for PC stalls
            if (cur_pc == prev_pc) {
                stall_cycles++;
                if (stall_cycles > STALL_THRESHOLD) {
                    std::cout << "HANG_DETECTED at cycle=" << i << " PC=0x" << std::hex << cur_pc
                              << " (stalled for " << stall_cycles << " cycles)" << std::dec << std::endl;
                    // Print last 128 PCs to diagnose
                    std::cout << "  last 128 PCs:" << std::endl;
                    uint32_t start = (pc_trace_idx > 128) ? pc_trace_idx - 128 : 0;
                    for (uint32_t j = start; j < pc_trace_idx; ++j) {
                        uint32_t p = pc_trace[j % 128];
                        std::cout << "0x" << std::hex << p << std::dec << " ";
                        if ((j - start + 1) % 8 == 0) std::cout << std::endl;
                    }
                    std::cout << std::endl;
                    return false;
                }
            } else {
                stall_cycles = 0;  // Reset stall counter on PC change
            }
            
            // Print first 50 PCs to see the actual execution path
            if (debug_output && i < 50) {
                std::cout << "CYCLE=" << i << " PC=0x" << std::hex << cur_pc << std::dec << std::endl;
            }
            // Detailed trace around ret instruction
            if (debug_output && cur_pc >= 0x440 && cur_pc <= 0x460) {
                uint32_t saved_ra = readMemWord(0x1FF9C);
                uint32_t saved_s0 = readMemWord(0x1FF98);
                std::cout << "@" << i << " PC=0x" << std::hex << cur_pc
                          << " [sp+156]=0x" << saved_ra
                          << " [sp+152]=0x" << saved_s0
                          << std::dec;
                if (cur_pc == 0x444) {
                    std::cout << " *** EPILOGUE: loading ra from [sp+156]";
                }
                std::cout << std::endl;
            }
            // Dump full stack frame at PC=0x450 (ret) to see what ra is being used
            if (debug_output && cur_pc == 0x450) {
                uint32_t actual_sp = getDebugSp();
                std::cout << "--- STACK FRAME DUMP at PC=0x450 (ret) ---" << std::endl;
                std::cout << "  Actual sp=0x" << std::hex << actual_sp << std::dec << std::endl;
                
                // Calculate expected sp (should be 0x1FF00 before addi sp, sp, 160)
                uint32_t expected_sp = actual_sp - 160;
                std::cout << "  Expected sp before epilogue=0x" << std::hex << expected_sp << std::dec << std::endl;
                
                for (uint32_t off = 0; off < 160; off += 4) {
                    uint32_t addr = expected_sp + off;
                    uint32_t val = readMemWord(addr);
                    std::cout << "  [sp+" << std::dec << off << "] = 0x" << std::hex << val << std::dec;
                    if (off == 156) std::cout << " ← saved ra (will become PC!)";
                    if (off == 152) std::cout << " ← saved s0";
                    if (off >= 4 && off <= 32) std::cout << " ← nmatvec descriptor area";
                    std::cout << std::endl;
                }
                std::cout << "--- END STACK DUMP ---" << std::endl;
                
                // Dump actual register values from memory-mapped interface
                uint32_t reg_ra = readReg(1);   // x1 = ra
                uint32_t reg_sp = readReg(2);   // x2 = sp
                uint32_t reg_s0 = readReg(8);   // x8 = s0
                uint32_t reg_a0 = readReg(10);  // x10 = a0
                std::cout << "--- REGISTER DUMP ---" << std::endl;
                std::cout << "  ra(x1)=0x" << std::hex << reg_ra << std::dec;
                std::cout << " (debug_ra=0x" << std::hex << getDebugRa() << std::dec << ")" << std::endl;
                std::cout << "  sp(x2)=0x" << std::hex << reg_sp << std::dec;
                std::cout << " (debug_sp=0x" << std::hex << getDebugSp() << std::dec << ")" << std::endl;
                std::cout << "  s0(x8)=0x" << std::hex << reg_s0 << std::dec << std::endl;
                std::cout << "  a0(x10)=0x" << std::hex << reg_a0 << std::dec << std::endl;
                
                // Check if sp is correct
                if (expected_sp == 0x1FF00) {
                    std::cout << "  ✓ sp is CORRECT (0x1FF00)" << std::endl;
                } else {
                    std::cout << "  ✗ sp is WRONG! Expected 0x1FF00, got 0x" << std::hex << expected_sp << std::dec << std::endl;
                }
                
                std::cout << "--- END REGISTER DUMP ---" << std::endl;
            }
            // Detect jump to model data (invalid instruction execution)
            if (cur_pc >= 0x30000 && cur_pc < 0xE0000) {
                if (debug_output) {
                    std::cout << "ERROR: Jump to model/data region at cycle=" << i << " PC=0x" << std::hex << cur_pc << std::dec << std::endl;
                    std::cout << "  This indicates execution of non-instruction data!" << std::endl;
                }
                // Halt simulation on invalid execution
                top_->halted = 1;
                top_->exit_code = 1;
                return false;
            }
            // If we just came from PC=0x450 (ret), check what saved_ra value is NOW
            // Watch for writes to 0x1FF7C (where run_forward_pass saves ra)
            if (debug_output) {
                uint32_t guarded_val = readMemWord(0x1FF7C);
                static uint32_t last_guarded = 0xFFFFFFFF;
                // Only log interesting changes (after prologue initializes it to 0x06B8)
                if (guarded_val != last_guarded) {
                    if (last_guarded != 0xFFFFFFFF) {
                        std::cout << "MEMWATCH cycle=" << i << " [0x1FF7C]=0x" << std::hex << guarded_val
                                  << " PC=0x" << prev_pc << "->0x" << cur_pc << std::dec;
                        if (guarded_val == 0x30000) {
                            std::cout << " (model_base stored at [sp+124])";
                        }
                        std::cout << std::endl;
                    }
                    last_guarded = guarded_val;
                }
            }
            if (debug_output && prev_pc == 0x450) {
                iteration_count++;
                uint32_t saved_ra_now = readMemWord(0x1FF9C);
                uint32_t saved_s0_now = readMemWord(0x1FFA0);
                uint32_t model_base = readMemWord(0x1FF7C);  // model_base stored at [sp+124]
                uint32_t model_base2 = readMemWord(0x1FF7C + 4);
                uint32_t model_base0 = readMemWord(0x1FF7C - 4);
                uint32_t actual_sp = getDebugSp();
                uint32_t actual_ra = getDebugRa();
                
                std::cout << "AFTER_RET cycle=" << i << " from PC=0x450 to PC=0x" << std::hex << cur_pc
                          << std::dec << " sp=0x" << std::hex << actual_sp
                          << " ra=0x" << actual_ra << " (iteration " << iteration_count << ")" << std::dec << std::endl;
                std::cout << "  [0x1FF9C]=0x" << std::hex << saved_ra_now << " (saved ra)"
                          << " [0x1FFA0]=0x" << saved_s0_now << " (saved s0)" << std::dec << std::endl;
                std::cout << "  [0x1FF7C]=0x" << std::hex << model_base << " (model_base)"
                          << " [0x1FF78]=0x" << model_base0 << " [0x1FF80]=0x" << model_base2 << std::dec << std::endl;
                
                // Check if the return address is correct
                if (cur_pc == 0x6B8) {
                    std::cout << "  ✓ CORRECT: jumped to 0x6B8 (return address)" << std::endl;
                } else if (cur_pc >= 0x30000 && cur_pc < 0x40000) {
                    std::cout << "  ✗ ERROR: jumped to model data 0x" << std::hex << cur_pc << std::dec << "!" << std::endl;
                } else {
                    std::cout << "  ? UNKNOWN: jumped to 0x" << std::hex << cur_pc << std::dec << std::endl;
                }
            }
            prev_pc = cur_pc;
            

            
            tick();
            
            // Check for syscall
            if (top_->syscall_valid) {
                handleSyscall();
            }
            
        if (top_->halted) {
            std::cout << "HALT at cycle=" << i << " pc=0x" << std::hex << getDebugPc() << std::dec
                      << " exit_code=" << (int)top_->exit_code << std::endl;
            uint32_t pc_val = getDebugPc();
            uint32_t instr = readMemWord(pc_val);
            std::cout << "  instruction=0x" << std::hex << instr << std::dec << std::endl;
            
            // Check if halt was in model/data region
            if (pc_val >= 0x30000 && pc_val < 0xE0000) {
                if (debug_output) {
                    std::cout << "  ERROR: Halted in model/data region (0x30000-0xDFFFF)!" << std::endl;
                    std::cout << "  This indicates execution of non-instruction data." << std::endl;
                }
            } else if (debug_output && i < 10000) {
                std::cout << "  WARNING: Early halt at cycle " << i << " (expected ~500K+)" << std::endl;
            }
                // Print last 128 PC values
                std::cout << "  last 128 PCs:" << std::endl;
                uint32_t start = (pc_trace_idx > 128) ? pc_trace_idx - 128 : 0;
                for (uint32_t j = start; j < pc_trace_idx; ++j) {
                    uint32_t p = pc_trace[j % 128];
                    std::cout << "0x" << std::hex << p << std::dec << " ";
                    if ((j - start + 1) % 8 == 0) std::cout << std::endl;
                }
                std::cout << std::endl;
            }
        }
        

        std::cout << "Execution completed. Cycles: " << final_cycle_count << ", Iterations: " << iteration_count << std::endl;
        
        top_->force_a0_en = 0;
        
        return top_->halted && !syscall_error_;
    }

    bool runUntilDone(uint32_t max_cycles, uint32_t done_addr, bool hold_char = false, uint32_t char_code = 0,
                      uint32_t key_addr = 0, uint32_t key_value = 0) {
        // Handle syscalls in testbench
        top_->syscall_done = 0;
        top_->syscall_ret = 0;
        syscall_error_ = false;
        syscall_error_num_ = 0;
        top_->force_a0_en = hold_char ? 1 : 0;
        top_->force_a0_data = char_code;

        bool key_written = false;
        for (uint32_t i = 0; i < max_cycles && !top_->halted && !syscall_error_; ++i) {
            tick();

            if (top_->syscall_valid) {
                handleSyscall();
            }

            if (readMem(done_addr) == 1) {
                // Done flag just set — write key immediately so it's fresh
                // for the next MODEL_MAP_INPUT at the top of the game loop.
                if (key_addr != 0 && !key_written) {
                    writeMem(key_addr + 0, key_value & 0xFF);
                    writeMem(key_addr + 1, (key_value >> 8) & 0xFF);
                    writeMem(key_addr + 2, (key_value >> 16) & 0xFF);
                    writeMem(key_addr + 3, (key_value >> 24) & 0xFF);
                    key_written = true;
                }
                break;
            }
            key_written = false;  // Reset when game loop continues
        }
        top_->force_a0_en = 0;

        return top_->halted && !syscall_error_;
    }

    bool runFrame(uint32_t frame_cycles, uint32_t max_cycles, uint32_t done_addr,
                  bool hold_char = false, uint32_t char_code = 0) {
        top_->syscall_done = 0;
        top_->syscall_ret = 0;
        syscall_error_ = false;
        syscall_error_num_ = 0;
        top_->force_a0_en = hold_char ? 1 : 0;
        top_->force_a0_data = char_code;

        bool done_start = readMem(done_addr) != 0;
        uint32_t budget = done_start ? frame_cycles : max_cycles;

        for (uint32_t i = 0; i < budget && !top_->halted && !syscall_error_; ++i) {
            tick();

            if (top_->syscall_valid) {
                handleSyscall();
            }

            if (!done_start && readMem(done_addr) == 1) {
                break;
            }
        }
        top_->force_a0_en = 0;

        return top_->halted && !syscall_error_;
    }
    
    void handleSyscall() {
        uint32_t num = top_->syscall_num;
        uint32_t a0 = top_->syscall_a0;
        uint32_t a1 = top_->syscall_a1;
        uint32_t a2 = top_->syscall_a2;
        uint32_t a3 = top_->syscall_a3;
        uint32_t a4 = top_->syscall_a4;
        uint32_t a5 = top_->syscall_a5;
        
        uint32_t ret = 0;
        
        switch (num) {
            case 64: { // write(fd, buf, count)
                if (a0 == 1 || a0 == 2) {  // stdout/stderr
                    for (uint32_t i = 0; i < a2; ++i) {
                        char c = readMem(a1 + i);
                        std::cout << c;
                    }
                    std::cout.flush();
                    ret = a2;
                } else if (a0 >= 3) {
                    auto it = open_files_.find(static_cast<int>(a0));
                    if (it == open_files_.end()) {
                        ret = static_cast<uint32_t>(-1);
                        break;
                    }

                    std::fstream* file = it->second;
                    uint32_t bytes_written = 0;
                    for (uint32_t i = 0; i < a2; ++i) {
                        file->put(static_cast<char>(readMem(a1 + i)));
                        bytes_written++;
                    }
                    file->flush();
                    file_positions_[static_cast<int>(a0)] += bytes_written;
                    ret = bytes_written;
                } else {
                    ret = static_cast<uint32_t>(-1);
                }
                break;
            }
                
            case 93:  // exit
                // Handled by CPU
                break;

            case 56: { // openat(dirfd, pathname, flags, mode)
                (void)a0;  // dirfd ignored in this simplified implementation
                (void)a3;  // mode ignored

                std::string filename;
                for (uint32_t i = 0; i < 256; ++i) {
                    char c = static_cast<char>(readMem(a1 + i));
                    if (c == '\0') {
                        break;
                    }
                    filename += c;
                }

                const uint32_t O_RDONLY = 0;
                const uint32_t O_WRONLY = 1;
                const uint32_t O_RDWR = 2;
                const uint32_t O_CREAT = 0x40;
                const uint32_t O_APPEND = 0x400;

                uint32_t open_mode_bits = (a2 & 3);
                std::ios::openmode mode_flags = std::ios::binary;
                if (open_mode_bits == O_RDONLY) {
                    mode_flags |= std::ios::in;
                } else if (open_mode_bits == O_WRONLY) {
                    mode_flags |= std::ios::out;
                } else if (open_mode_bits == O_RDWR) {
                    mode_flags |= (std::ios::in | std::ios::out);
                }

                if (a2 & O_CREAT) {
                    mode_flags |= std::ios::trunc;
                }
                if (a2 & O_APPEND) {
                    mode_flags |= std::ios::app;
                }

                std::fstream* file = new std::fstream(filename, mode_flags);
                if (!file->is_open()) {
                    delete file;
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                int fd = next_fd_++;
                open_files_[fd] = file;
                file_positions_[fd] = 0;
                ret = static_cast<uint32_t>(fd);
                break;
            }

            case 63: { // read(fd, buf, count)
                int fd = static_cast<int>(a0);
                uint32_t buf = a1;
                uint32_t count = a2;

                if (fd == 0) {
                    ret = 0;
                    break;
                }

                auto it = open_files_.find(fd);
                if (it == open_files_.end()) {
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                std::fstream* file = it->second;
                uint32_t bytes_read = 0;
                for (uint32_t i = 0; i < count; ++i) {
                    int c = file->get();
                    if (c == EOF) {
                        break;
                    }
                    writeMem(buf + i, static_cast<uint8_t>(c));
                    bytes_read++;
                }

                file_positions_[fd] += bytes_read;
                ret = bytes_read;
                break;
            }

            case 57: { // close(fd)
                int fd = static_cast<int>(a0);
                if (fd < 3) {
                    ret = 0;
                    break;
                }

                auto it = open_files_.find(fd);
                if (it == open_files_.end()) {
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                it->second->close();
                delete it->second;
                open_files_.erase(it);
                file_positions_.erase(fd);
                ret = 0;
                break;
            }

            case 19: { // lseek(fd, offset, whence)
                int fd = static_cast<int>(a0);
                int32_t offset = static_cast<int32_t>(a1);
                int whence = static_cast<int>(a2);

                auto it = open_files_.find(fd);
                if (it == open_files_.end()) {
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                std::fstream* file = it->second;
                auto pos_it = file_positions_.find(fd);
                uint32_t current_pos = (pos_it != file_positions_.end()) ? pos_it->second : 0;
                uint32_t new_position = 0;

                switch (whence) {
                    case 0: {  // SEEK_SET
                        if (offset < 0) {
                            ret = static_cast<uint32_t>(-1);
                            break;
                        }
                        new_position = static_cast<uint32_t>(offset);
                        break;
                    }
                    case 1: {  // SEEK_CUR
                        int32_t result = static_cast<int32_t>(current_pos) + offset;
                        if (result < 0) {
                            ret = static_cast<uint32_t>(-1);
                            break;
                        }
                        new_position = static_cast<uint32_t>(result);
                        break;
                    }
                    case 2: {  // SEEK_END
                        file->clear();
                        file->seekg(0, std::ios::end);
                        std::streampos end_pos = file->tellg();
                        if (end_pos < 0) {
                            ret = static_cast<uint32_t>(-1);
                            break;
                        }
                        int32_t file_size = static_cast<int32_t>(end_pos);
                        int32_t result = file_size + offset;
                        if (result < 0) {
                            ret = static_cast<uint32_t>(-1);
                            break;
                        }
                        new_position = static_cast<uint32_t>(result);
                        break;
                    }
                    default:
                        ret = static_cast<uint32_t>(-1);
                        break;
                }
                if (ret == static_cast<uint32_t>(-1)) {
                    break;
                }

                file->clear();
                file->seekg(static_cast<std::streamoff>(new_position), std::ios::beg);
                file->seekp(static_cast<std::streamoff>(new_position), std::ios::beg);
                file_positions_[fd] = new_position;
                ret = new_position;
                break;
            }
                
            case 214:  // brk
                if (a0 == 0) {
                    ret = heap_break_;
                } else if (a0 < MEM_SIZE) {
                    heap_break_ = a0;
                    ret = heap_break_;
                } else {
                    ret = heap_break_;
                }
                break;

            case 192: { // mmap2(addr, len, prot, flags, fd, offset)
                (void)a2;  // prot unused
                (void)a4;  // fd unused for anonymous mappings
                (void)a5;  // offset unused for anonymous mappings

                const uint32_t MAP_ANONYMOUS = 0x20;
                const uint32_t MAP_FIXED = 0x10;

                if ((a3 & MAP_ANONYMOUS) == 0) {
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                uint32_t aligned_len = (a1 + 0xFFF) & ~0xFFF;
                uint32_t result_addr = 0;

                if (a3 & MAP_FIXED) {
                    if (a0 + aligned_len > MEM_SIZE) {
                        ret = static_cast<uint32_t>(-1);
                        break;
                    }
                    result_addr = a0;
                } else {
                    if (mmap_base_ + aligned_len > MEM_SIZE) {
                        ret = static_cast<uint32_t>(-1);
                        break;
                    }
                    result_addr = mmap_base_;
                    mmap_base_ += aligned_len;
                }

                mmap_regions_[result_addr] = aligned_len;
                for (uint32_t i = 0; i < aligned_len; ++i) {
                    writeMem(result_addr + i, 0);
                }
                ret = result_addr;
                break;
            }

            case 215: { // munmap(addr, len)
                auto it = mmap_regions_.find(a0);
                if (it == mmap_regions_.end()) {
                    ret = static_cast<uint32_t>(-1);
                    break;
                }

                uint32_t aligned_len = (a1 + 0xFFF) & ~0xFFF;
                if (it->second != aligned_len && it->second != a1) {
                    if (a0 + a1 > MEM_SIZE) {
                        ret = static_cast<uint32_t>(-1);
                        break;
                    }
                }

                mmap_regions_.erase(it);
                ret = 0;
                break;
            }
                
            default:
                std::cerr << "Unknown syscall: " << num << std::endl;
                syscall_error_ = true;
                syscall_error_num_ = num;
                ret = static_cast<uint32_t>(-1);
                break;
        }
        
        top_->syscall_ret = ret;
        top_->syscall_done = 1;
        tick();
        top_->syscall_done = 0;
    }
    
    bool isHalted() const { return top_->halted; }
    uint32_t getExitCode() const { return top_->exit_code; }
    uint32_t getCycleCount() const { return top_->cycle_count; }
    bool hasSyscallError() const { return syscall_error_; }
    uint32_t getSyscallErrorNum() const { return syscall_error_num_; }
    uint32_t getDebugPc() const { return top_->debug_pc; }
    uint32_t getDebugRa() const { return top_->debug_ra; }
    uint32_t getDebugSp() const { return top_->debug_sp; }
    
    uint32_t readReg(uint8_t reg) {
        uint32_t addr = 0x100000 + static_cast<uint32_t>(reg) * 4u;
        return readMemWord(addr);
    }
    
    void renderFramebuffer() {
        std::cout << "\r\n";
        for (int y = 0; y < 15; ++y) {
            for (int x = 0; x < 20; ++x) {
                uint8_t pixel = readMem(FRAMEBUFFER_ADDR + y * FRAMEBUFFER_STRIDE + x);
                std::cout << (pixel > 127 ? '#' : ' ');
            }
            std::cout << "\r\n";
        }
        for (int y = 15; y < 20; ++y) {
            std::cout << "\r\n";
        }
        std::cout << std::flush;
    }
    
    void getFramebuffer(uint8_t* buffer) {
        for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
            buffer[i] = readMem(FRAMEBUFFER_ADDR + i);
        }
    }

private:
    Vemulator_top* top_;
    VerilatedVcdC* trace_;
    uint64_t time_;
    uint32_t heap_break_ = 0x1000;
    uint32_t mmap_base_ = 0x10000;
    int next_fd_ = 3;
    std::unordered_map<int, std::fstream*> open_files_;
    std::unordered_map<int, uint32_t> file_positions_;
    std::unordered_map<uint32_t, uint32_t> mmap_regions_;
    bool syscall_error_ = false;
    uint32_t syscall_error_num_ = 0;
};

static volatile sig_atomic_t g_should_exit = 0;

void signal_handler(int signum) {
    if (signum == SIGINT) {
        g_should_exit = 1;
    }
}

struct TerminalMode {
    termios original_settings{};
    bool active = false;

    TerminalMode() {
        if (!isatty(STDIN_FILENO)) {
            return;  // Don't set raw mode on PTY slave (e.g., automated testing)
        }
        if (tcgetattr(STDIN_FILENO, &original_settings) != 0) {
            return;
        }
        termios raw = original_settings;
        raw.c_lflag &= ~(ICANON | ECHO);
        raw.c_cc[VMIN] = 0;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == 0) {
            active = true;
        }
    }

    ~TerminalMode() {
        if (active) {
            tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_settings);
        }
    }
};

void process_gui_input(VerilatorRunner& runner, const char* binary_file, uint32_t initial_char, uint32_t cycles_per_frame, uint32_t max_cycles_per_frame, bool debug_output, bool auto_down = false) {
    // Skip terminal setup in PTY (e.g., automated testing)
    bool is_pty = !isatty(STDIN_FILENO);
    TerminalMode terminal;
    if (!is_pty) {
        std::signal(SIGINT, signal_handler);
    }
    g_should_exit = 0;

    uint32_t current_char = initial_char;
    if (debug_output) {
        std::cout << "GUI mode active. Press any key to change character. Ctrl+C to exit." << std::endl;
        std::cout << "Starting with character code " << current_char << "..." << std::endl;
        std::cout << "GUI cycles per frame: " << cycles_per_frame << std::endl;
        std::cout << "GUI max cycles per frame: " << max_cycles_per_frame << std::endl;
        if (auto_down) {
            std::cout << "Auto-down mode: sending 's' every frame" << std::endl;
        }
    } else {
        std::cout << "GUI mode active. Press any key to change character. Ctrl+C to exit." << std::endl;
    }

    // Initial render (like emulator_runner) so the first frame is visible
    // before waiting for user input.
    runner.writeMem(0x154004, initial_char & 0xFF);
    runner.run(max_cycles_per_frame, false, initial_char, false);
    std::cout << "\033[2J\033[H";
    runner.renderFramebuffer();

    uint32_t frame_count = 0;
    while (!g_should_exit) {
        if (auto_down) {
            current_char = 's';
            ++frame_count;
            if (debug_output) {
                std::cout << "Frame " << frame_count << ": auto-sending 's'" << std::endl;
            }
        } else {
            unsigned char ch = 0;
            if (read(STDIN_FILENO, &ch, 1) == 1) {
                current_char = static_cast<uint32_t>(ch);
            }
        }

        // Write key to memory-mapped 0x154004 for the game to read (4 bytes).

        if (auto_down) {
            // Auto-down: run until done flag, key written at done point
            runner.writeMem(0x154000, 0);
            runner.writeMem(0x154001, 0);
            runner.writeMem(0x154002, 0);
            runner.writeMem(0x154003, 0);
            runner.runUntilDone(max_cycles_per_frame, 0x154000, false, current_char,
                                0x154004, current_char);
        } else {
            // Interactive: run for fixed cycle budget, write key before run
            runner.writeMem(0x154004, current_char & 0xFF);
            runner.writeMem(0x154005, (current_char >> 8) & 0xFF);
            runner.writeMem(0x154006, (current_char >> 16) & 0xFF);
            runner.writeMem(0x154007, (current_char >> 24) & 0xFF);
            runner.run(max_cycles_per_frame, false, current_char, false);
        }

        std::cout << "\033[2J\033[H";
        runner.renderFramebuffer();

        if (runner.isHalted() || runner.hasSyscallError()) {
            std::cout << "GUI exit: halted=" << runner.isHalted()
                      << " syscall_error=" << runner.hasSyscallError()
                      << " exit_code=" << runner.getExitCode()
                      << " cycles=" << runner.getCycleCount()
                      << " pc=0x" << std::hex << runner.getDebugPc() << std::dec << std::endl;
            break;
        }
        usleep(10000);
    }

    std::cout << "\nGUI mode closed." << std::endl;
}

void process_movement_input(VerilatorRunner& runner) {
    TerminalMode terminal;
    std::signal(SIGINT, signal_handler);
    g_should_exit = 0;

    uint32_t current_state = 200;  // Center position (10,10 on 20x20 board)
    bool waiting_for_prediction = false;
    uint32_t pending_action = 4;  // No pending action initially
    uint32_t pending_state = current_state;

    std::cout << "Movement mode active. Use hjkl to move, 'q' to quit." << std::endl;
    std::cout << "h: left, j: down, k: up, l: right, space: stay" << std::endl;

    while (!g_should_exit) {
        unsigned char ch = 0;
        if (read(STDIN_FILENO, &ch, 1) == 1) {
            if (ch == 'q') {
                g_should_exit = 1;
                break;
            }

            if (!waiting_for_prediction) {
                // Map hjkl keys to movement actions
                uint32_t action_id = 4;  // Default: stay (action 4)
                if (ch == 'h') action_id = 2;  // left
                else if (ch == 'j') action_id = 1;  // down
                else if (ch == 'k') action_id = 0;  // up
                else if (ch == 'l') action_id = 3;  // right
                else if (ch == ' ') action_id = 4;  // stay

                // Store pending action and current state
                pending_action = action_id;
                pending_state = current_state;
                waiting_for_prediction = true;

                std::cout << "Key: '" << ch << "' Action: " << action_id;
                std::cout << " State: " << current_state << " (waiting for neural prediction)" << std::endl;
            }
        }

        // Pack state and action into a0 register for neural network
        uint32_t packed_code = pending_state | (pending_action << 9);
        runner.run(500000, true, packed_code);

        // Check if neural network produced output
        uint8_t fb[FRAMEBUFFER_SIZE];
        runner.getFramebuffer(fb);

        uint32_t new_state = current_state;
        uint8_t max_brightness = 0;
        uint32_t bright_pixel_count = 0;

        for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
            if (fb[i] > 0) {
                bright_pixel_count++;
            }
            if (fb[i] > max_brightness) {
                max_brightness = fb[i];
                new_state = i;
            }
        }

        std::cout << "Framebuffer stats: " << bright_pixel_count << " bright pixels, max brightness: " << (int)max_brightness << std::endl;

        // If we were waiting for a prediction and got valid output, process it
        if (waiting_for_prediction && max_brightness > 0 && new_state != current_state) {
            current_state = new_state;
            waiting_for_prediction = false;
            std::cout << "Neural prediction: moved to " << current_state;
            std::cout << " (x:" << (current_state % 20) << ", y:" << (current_state / 20) << ")" << std::endl;
        }

        std::cout << "\033[2J\033[H";
        runner.renderFramebuffer();

        if (runner.isHalted() || runner.hasSyscallError()) {
            break;
        }
        usleep(50000);
    }

    std::cout << "\nMovement mode closed." << std::endl;
}

void printUsage(const char* prog) {
    std::cerr << "Usage: " << prog << " <binary_file> [options]\n"
              << "Options:\n"
              << "  --gui                 Interactive GUI mode\n"
              << "  --gui-debug           Enable verbose debug output in GUI mode\n"
              << "  --gui-auto-down       Auto-send 's' every frame (implies --gui)\n"
              << "  --movement            Interactive movement mode (hjkl keys)\n"
              << "  --char <char>         Set a0 to ASCII code of character\n"
              << "  --char-code <code>    Set a0 to numeric code (uint32)\n"
              << "  --cycles <count>      Max cycles (default: 1000000)\n"
              << "  --verbose / -v        Print debug info\n"
              << "  --render-framebuffer  Render 20x20 framebuffer\n"
              << "  --dump-framebuffer    Dump 400 framebuffer bytes (hex)\n"
              << "  --gui-cycles <count>  Cycles per GUI frame (default 50000)\n"
              << "  --gui-max-cycles <count>  Max cycles per GUI frame if done flag never sets (default 5000000)\n"
              << "  --dump-memory <addr> <count>  Dump count 32-bit words at addr\n"
              << std::endl;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    
    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }
    
    const char* binary_file = argv[1];
    bool verbose = false;
    bool gui_mode = false;
    bool movement_mode = false;
    bool render_fb = false;
    bool dump_fb = false;
    bool gui_debug = false;  // Enable debug output in GUI mode
    bool gui_auto_down = false;  // Auto-send 's' every frame
    bool char_specified = false;
    bool trace_enabled = false;
    uint32_t char_code = 0;
    uint32_t max_cycles = 10000000;  // 10M cycles (~17 iterations)
    uint32_t gui_cycles = 600000;   // 600K cycles per frame (enough for 1 iteration)
    uint32_t gui_max_cycles = 5000000;

    struct DumpRegion {
        uint32_t addr;
        uint32_t count;
    };
    std::vector<DumpRegion> dump_regions;

    // Parse arguments
    for (int i = 2; i < argc; ++i) {
        if (strcmp(argv[i], "--verbose") == 0 || strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (strcmp(argv[i], "--gui") == 0) {
            gui_mode = true;
        } else if (strcmp(argv[i], "--movement") == 0) {
            movement_mode = true;
        } else if (strcmp(argv[i], "--render-framebuffer") == 0) {
            render_fb = true;
        } else if (strcmp(argv[i], "--dump-framebuffer") == 0) {
            dump_fb = true;
        } else if (strcmp(argv[i], "--gui-debug") == 0) {
            gui_debug = true;
        } else if (strcmp(argv[i], "--gui-auto-down") == 0) {
            gui_auto_down = true;
            gui_mode = true;  // implies --gui
        } else if (strcmp(argv[i], "--trace") == 0) {
            trace_enabled = true;
        } else if (strcmp(argv[i], "--char") == 0 && i + 1 < argc) {
            char_specified = true;
            char_code = static_cast<uint8_t>(argv[++i][0]);
        } else if (strcmp(argv[i], "--char-code") == 0 && i + 1 < argc) {
            char* end = nullptr;
            unsigned long long parsed = std::strtoull(argv[++i], &end, 0);
            if (end == argv[i] || *end != '\0' ||
                parsed > static_cast<unsigned long long>(std::numeric_limits<uint32_t>::max())) {
                std::cerr << "Error: --char-code must be an integer in [0, 4294967295]" << std::endl;
                return 1;
            }
            char_specified = true;
            char_code = static_cast<uint32_t>(parsed);
        } else if (strcmp(argv[i], "--cycles") == 0 && i + 1 < argc) {
            max_cycles = std::strtoul(argv[++i], nullptr, 0);
        } else if (strcmp(argv[i], "--gui-cycles") == 0 && i + 1 < argc) {
            gui_cycles = std::strtoul(argv[++i], nullptr, 0);
        } else if (strcmp(argv[i], "--gui-max-cycles") == 0 && i + 1 < argc) {
            gui_max_cycles = std::strtoul(argv[++i], nullptr, 0);
        } else if (strcmp(argv[i], "--dump-memory") == 0) {
            if (i + 2 < argc) {
                uint32_t addr = std::strtoul(argv[i+1], nullptr, 0);
                uint32_t count = std::strtoul(argv[i+2], nullptr, 0);
                dump_regions.push_back({addr, count});
                i += 2;
            } else {
                std::cerr << "Error: --dump-memory requires <addr> <count>" << std::endl;
                return 1;
            }
        }
    }
    
    // Read binary file
    std::ifstream file(binary_file, std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "Error: Could not open " << binary_file << std::endl;
        return 1;
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<uint8_t> buffer(size);
    if (!file.read(reinterpret_cast<char*>(buffer.data()), size)) {
        std::cerr << "Error: Could not read file" << std::endl;
        return 1;
    }
    
    if (verbose) {
        std::cout << "Loaded " << size << " bytes from " << binary_file << std::endl;
    }
    
    // Initialize emulator
    VerilatorRunner runner;
    if (trace_enabled) {
        runner.enableTrace("trace.vcd");
        if (verbose) {
            std::cout << "VCD tracing enabled: trace.vcd" << std::endl;
        }
    }
    runner.reset();
    
    // Load program
    uint32_t entry_point = 0;
    if (!runner.loadElf(buffer, entry_point)) {
        if (verbose) {
            std::cout << "Not an ELF file, loading as raw binary" << std::endl;
        }
        runner.loadRaw(buffer);
    } else {
        if (verbose) {
            std::cout << "Loaded ELF, entry point: 0x" << std::hex << entry_point << std::dec << std::endl;
        }
        // Set PC to ELF entry point
        runner.setPC(entry_point);
    }
    
    // Initialize stack pointer near top of simulated RAM (2MB default).
    runner.setReg(2, MEM_SIZE - 4);
    
    // Set character code if specified (a0 for legacy, key reg for memory-mapped)
    constexpr uint32_t KEY_REG_ADDR = 0x154004;
    if (char_specified) {
        runner.setReg(10, char_code);
        for (uint32_t b = 0; b < 4; ++b) {
            runner.writeMem(KEY_REG_ADDR + b, static_cast<uint8_t>((char_code >> (b * 8)) & 0xFF));
        }
        if (verbose) {
            std::cout << "Set key to " << char_code << " (a0 + mem@0x154004)" << std::endl;
        }
    } else if (gui_mode) {
        char_code = 32;
        runner.setReg(10, char_code);
        for (uint32_t b = 0; b < 4; ++b) {
            runner.writeMem(KEY_REG_ADDR + b, static_cast<uint8_t>((char_code >> (b * 8)) & 0xFF));
        }
    }
    
    // Run
    if (verbose) {
        std::cout << "Starting execution with max " << max_cycles << " cycles..." << std::endl;
    }
    
    runner.start();
    if (movement_mode) {
        process_movement_input(runner);
    } else if (gui_mode) {
        // Attempt to match emulator_runner GUI frame cadence by waiting
        // for the done flag, but cap cycles to avoid hanging if it never sets.
        process_gui_input(runner, binary_file, char_code, gui_cycles, gui_max_cycles, gui_debug, gui_auto_down);
    } else {
        // hold_char=false: key is read from memory-mapped reg 0x154004, not forced a0
        runner.run(max_cycles, false, 0);
    }
    if (runner.hasSyscallError()) {
        if (verbose) {
            std::cerr << "Execution stopped on unsupported syscall "
                      << runner.getSyscallErrorNum() << std::endl;
        }
        return 1;
    }
    
    if (verbose) {
        std::cout << "Execution complete. Cycles: " << runner.getCycleCount() << std::endl;
        if (runner.isHalted()) {
            std::cout << "Program exited normally" << std::endl;
        } else {
            std::cout << "Program reached cycle limit" << std::endl;
        }
    }

    if (dump_fb) {
        uint8_t fb[FRAMEBUFFER_SIZE];
        runner.getFramebuffer(fb);
        std::ios::fmtflags old_flags = std::cout.flags();
        char old_fill = std::cout.fill();
        std::cout << "FRAMEBUFFER_HEX:";
        for (uint32_t i = 0; i < FRAMEBUFFER_SIZE; ++i) {
            std::cout << std::hex << std::setw(2) << std::setfill('0')
                      << static_cast<unsigned>(fb[i]);
        }
        std::cout.flags(old_flags);
        std::cout.fill(old_fill);
        std::cout << std::endl;
    }

    // Dump memory regions
    for (const auto& region : dump_regions) {
        std::cout << "Memory Dump at 0x" << std::hex << region.addr << std::dec << ":" << std::endl;
        for (uint32_t i = 0; i < region.count; ++i) {
            uint32_t addr = region.addr + i * 4;
            uint32_t val = static_cast<uint32_t>(runner.readMem(addr)) |
                          (static_cast<uint32_t>(runner.readMem(addr + 1)) << 8) |
                          (static_cast<uint32_t>(runner.readMem(addr + 2)) << 16) |
                          (static_cast<uint32_t>(runner.readMem(addr + 3)) << 24);
            std::ios::fmtflags old_flags = std::cout.flags();
            char old_fill = std::cout.fill();
            std::cout << "0x" << std::hex << std::setw(8) << std::setfill('0') << addr << ": ";
            std::cout << "0x" << std::setw(8) << std::setfill('0') << val;
            float f_val;
            std::memcpy(&f_val, &val, sizeof(float));
            std::cout << " (" << std::dec << std::setprecision(6) << f_val << ")" << std::endl;
            std::cout.flags(old_flags);
            std::cout.fill(old_fill);
        }
    }

    // Render framebuffer if requested
    if (render_fb) {
        runner.renderFramebuffer();
    }
    
    return runner.getExitCode();
}
