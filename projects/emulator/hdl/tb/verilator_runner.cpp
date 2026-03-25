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
constexpr uint32_t MEM_SIZE = 0x100000;  // Keep in sync with emulator_top default

#include <verilated_vcd_c.h>

class VerilatorRunner {
public:
    VerilatorRunner() : top_(new Vemulator_top), time_(0), trace_(nullptr) {
        top_->clk = 0;
        top_->rst_n = 0;
        top_->start = 0;
        top_->reg_write_en = 0;
        top_->mem_init_en = 0;
    }
    
    ~VerilatorRunner() {
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
    
    void setReg(uint8_t reg, uint32_t value) {
        top_->reg_write_en = 1;
        top_->reg_write_addr = reg;
        top_->reg_write_data = value;
        tick();
        top_->reg_write_en = 0;
    }
    
    void setPC(uint32_t pc) {
        // PC is set through register initialization
        // In our design, we'd need to add a PC init port
        // For now, ELF entry point handles this
    }
    
    void start() {
        top_->start = 1;
        tick();
        top_->start = 0;
    }
    
    bool run(uint32_t max_cycles) {
        // Handle syscalls in testbench
        top_->syscall_done = 0;
        top_->syscall_ret = 0;
        syscall_error_ = false;
        syscall_error_num_ = 0;
        
        for (uint32_t i = 0; i < max_cycles && !top_->halted && !syscall_error_; ++i) {
            tick();
            
            // Check for syscall
            if (top_->syscall_valid) {
                handleSyscall();
            }
        }
        
        return top_->halted && !syscall_error_;
    }
    
    void handleSyscall() {
        uint32_t num = top_->syscall_num;
        uint32_t a0 = top_->syscall_a0;
        uint32_t a1 = top_->syscall_a1;
        uint32_t a2 = top_->syscall_a2;
        
        uint32_t ret = 0;
        
        switch (num) {
            case 64:  // write
                if (a0 == 1 || a0 == 2) {  // stdout/stderr
                    for (uint32_t i = 0; i < a2; ++i) {
                        char c = readMem(a1 + i);
                        std::cout << c;
                    }
                    ret = a2;
                }
                break;
                
            case 93:  // exit
                // Handled by CPU
                break;
                
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
    
    void renderFramebuffer() {
        std::cout << "\n";
        for (int y = 0; y < 20; ++y) {
            for (int x = 0; x < 20; ++x) {
                uint8_t pixel = readMem(FRAMEBUFFER_ADDR + y * 20 + x);
                std::cout << (pixel > 127 ? '#' : ' ');
            }
            std::cout << "\n";
        }
        std::cout << std::endl;
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
    bool syscall_error_ = false;
    uint32_t syscall_error_num_ = 0;
};

void printUsage(const char* prog) {
    std::cerr << "Usage: " << prog << " <binary_file> [options]\n"
              << "Options:\n"
              << "  --gui                 Interactive GUI mode (not supported in Verilator)\n"
              << "  --char <char>         Set a0 to ASCII code of character\n"
              << "  --char-code <code>    Set a0 to numeric code (0-255)\n"
              << "  --cycles <count>      Max cycles (default: 1000000)\n"
              << "  --verbose / -v        Print debug info\n"
              << "  --render-framebuffer  Render 20x20 framebuffer\n"
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
    bool render_fb = false;
    bool char_specified = false;
    bool trace_enabled = false;
    uint32_t char_code = 0;
    uint32_t max_cycles = 1000000;
    
    // Parse arguments
    for (int i = 2; i < argc; ++i) {
        if (strcmp(argv[i], "--verbose") == 0 || strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (strcmp(argv[i], "--render-framebuffer") == 0) {
            render_fb = true;
        } else if (strcmp(argv[i], "--trace") == 0) {
            trace_enabled = true;
        } else if (strcmp(argv[i], "--gui") == 0) {
            std::cerr << "Warning: --gui not supported in Verilator runner" << std::endl;
        } else if (strcmp(argv[i], "--char") == 0 && i + 1 < argc) {
            char_specified = true;
            char_code = static_cast<uint8_t>(argv[++i][0]);
        } else if (strcmp(argv[i], "--char-code") == 0 && i + 1 < argc) {
            char_specified = true;
            char_code = std::strtoul(argv[++i], nullptr, 0);
        } else if (strcmp(argv[i], "--cycles") == 0 && i + 1 < argc) {
            max_cycles = std::strtoul(argv[++i], nullptr, 0);
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
    } else if (verbose) {
        std::cout << "Loaded ELF, entry point: 0x" << std::hex << entry_point << std::dec << std::endl;
    }
    
    // Initialize stack pointer near top of simulated RAM (1MB default).
    runner.setReg(2, MEM_SIZE - 4);
    
    // Set character code if specified
    if (char_specified) {
        runner.setReg(10, char_code);
        if (verbose) {
            std::cout << "Set a0 (x10) to " << char_code << std::endl;
        }
    }
    
    // Run
    if (verbose) {
        std::cout << "Starting execution with max " << max_cycles << " cycles..." << std::endl;
    }
    
    runner.start();
    runner.run(max_cycles);
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
    
    // Render framebuffer if requested
    if (render_fb) {
        runner.renderFramebuffer();
    }
    
    return runner.getExitCode();
}
