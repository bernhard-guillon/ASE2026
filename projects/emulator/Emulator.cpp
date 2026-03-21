#include "Emulator.h"
#include <iostream>
#include <stdexcept>

Emulator::Emulator(size_t memory_size) 
    : cpu_(), memory_(memory_size), halted_(false), exit_code_(0), heap_break_(0x1000), 
      mmap_base_(0x10000), next_fd_(3) {  // FDs 0,1,2 are stdin, stdout, stderr
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
            // Exit code is in a0 (x10)
            exit_code_ = cpu_.getReg(10);
            break;
        }
        
        case 214: { // brk(addr)
            // This simple implementation just tracks the break
            // In a real kernel, this would manage the heap
            uint32_t new_break = cpu_.getReg(10);  // a0 has requested break address
            
            // If new_break is 0, just return current break
            if (new_break == 0) {
                cpu_.setReg(10, heap_break_);
            } else if (new_break <= memory_.size()) {
                // Allow setting break if within memory bounds
                heap_break_ = new_break;
                cpu_.setReg(10, heap_break_);
            } else {
                // Return old break if requested address is out of bounds
                cpu_.setReg(10, heap_break_);
            }
            
            cpu_.incrementPC();
            break;
        }
        
        case 192: { // mmap2(addr, len, prot, flags, fd, offset)
            // On RV32, mmap2 is the standard mmap variant
            uint32_t addr = cpu_.getReg(10);    // a0 - desired address (0 = let kernel choose)
            uint32_t len = cpu_.getReg(11);     // a1 - length
            uint32_t prot = cpu_.getReg(12);    // a2 - protection flags (unused)
            uint32_t flags = cpu_.getReg(13);   // a3 - flags (MAP_ANONYMOUS=0x20, MAP_FIXED=0x10)
            uint32_t fd = cpu_.getReg(14);      // a4 - file descriptor
            uint32_t offset = cpu_.getReg(15);  // a5 - offset (unused for MAP_ANONYMOUS)
            
            // Simple mmap implementation: only support MAP_ANONYMOUS
            const uint32_t MAP_ANONYMOUS = 0x20;
            const uint32_t MAP_FIXED = 0x10;
            
            if ((flags & MAP_ANONYMOUS) == 0) {
                // File-backed mmap not supported
                cpu_.setReg(10, static_cast<uint32_t>(-1));
                cpu_.incrementPC();
                break;
            }
            
            // Page-align length (4096-byte pages)
            uint32_t aligned_len = (len + 0xFFF) & ~0xFFF;
            
            uint32_t result_addr;
            
            if (flags & MAP_FIXED) {
                // Caller specifies address
                if (addr + aligned_len > memory_.size()) {
                    // Out of bounds
                    cpu_.setReg(10, static_cast<uint32_t>(-1));
                    cpu_.incrementPC();
                    break;
                }
                result_addr = addr;
            } else {
                // Kernel chooses address (use our mmap_base)
                if (mmap_base_ + aligned_len > memory_.size()) {
                    // Out of memory
                    cpu_.setReg(10, static_cast<uint32_t>(-1));
                    cpu_.incrementPC();
                    break;
                }
                result_addr = mmap_base_;
                mmap_base_ += aligned_len;
            }
            
            // Track this allocation
            mmap_regions_[result_addr] = aligned_len;
            
            // Zero-initialize the region (typical mmap behavior)
            for (uint32_t i = 0; i < aligned_len; ++i) {
                memory_.write8(result_addr + i, 0);
            }
            
            // Return allocated address
            cpu_.setReg(10, result_addr);
            cpu_.incrementPC();
            break;
        }
        
        case 215: { // munmap(addr, len)
            uint32_t addr = cpu_.getReg(10);    // a0 - address
            uint32_t len = cpu_.getReg(11);     // a1 - length
            
            // Find if this address is in our tracked regions
            auto it = mmap_regions_.find(addr);
            if (it == mmap_regions_.end()) {
                // Address not found or invalid
                cpu_.setReg(10, static_cast<uint32_t>(-1));
                cpu_.incrementPC();
                break;
            }
            
            // Check if length matches (we track by exact address/size)
            uint32_t aligned_len = (len + 0xFFF) & ~0xFFF;
            if (it->second != aligned_len && it->second != len) {
                // Length mismatch - still allow if within bounds
                // This is a simplification; real munmap is more flexible
                if (addr + len > memory_.size()) {
                    cpu_.setReg(10, static_cast<uint32_t>(-1));
                    cpu_.incrementPC();
                    break;
                }
            }
            
            // Remove from tracking (in real kernel, we'd mark pages as unmapped)
            mmap_regions_.erase(it);
            
            // Return success
            cpu_.setReg(10, 0);
            cpu_.incrementPC();
            break;
        }
        
        case 56: { // openat(dirfd, pathname, flags, mode)
            // Simplified: ignore dirfd (assume CWD), ignore mode
            uint32_t dirfd = cpu_.getReg(10);   // a0 (usually -100 for CWD)
            uint32_t pathname = cpu_.getReg(11); // a1 - path string
            uint32_t flags = cpu_.getReg(12);    // a2 - open flags
            uint32_t mode = cpu_.getReg(13);     // a3 - file mode (permission bits)
            
            // Read filename from memory
            std::string filename;
            for (uint32_t i = 0; i < 256; ++i) {  // Max 256 char filename
                char c = static_cast<char>(memory_.read8(pathname + i));
                if (c == '\0') break;
                filename += c;
            }
            
            // Map flags: O_RDONLY=0, O_WRONLY=1, O_RDWR=2, O_CREAT=0x40, O_APPEND=0x400
            const uint32_t O_RDONLY = 0;
            const uint32_t O_WRONLY = 1;
            const uint32_t O_RDWR = 2;
            const uint32_t O_CREAT = 0x40;
            const uint32_t O_APPEND = 0x400;
            
            int open_mode_bits = (flags & 3);  // Extract read/write mode
            
            std::ios::openmode mode_flags = std::ios::binary;
            if (open_mode_bits == O_RDONLY) {
                mode_flags |= std::ios::in;
            } else if (open_mode_bits == O_WRONLY) {
                mode_flags |= std::ios::out;
            } else if (open_mode_bits == O_RDWR) {
                mode_flags |= (std::ios::in | std::ios::out);
            }
            
            if (flags & O_CREAT) {
                mode_flags |= std::ios::trunc;
            }
            if (flags & O_APPEND) {
                mode_flags |= std::ios::app;
            }
            
            // Try to open file
            std::fstream *file = new std::fstream(filename, mode_flags);
            if (!file->is_open()) {
                delete file;
                cpu_.setReg(10, static_cast<uint32_t>(-1));  // errno would be set in real kernel
                cpu_.incrementPC();
                break;
            }
            
            // Assign file descriptor
            int fd = next_fd_++;
            open_files_[fd] = file;
            
            // Return file descriptor
            cpu_.setReg(10, fd);
            cpu_.incrementPC();
            break;
        }
        
        case 63: { // read(fd, buf, count)
            int fd = cpu_.getReg(10);            // a0 - file descriptor
            uint32_t buf = cpu_.getReg(11);      // a1 - buffer address
            uint32_t count = cpu_.getReg(12);    // a2 - bytes to read
            
            if (fd == 0) {
                // stdin not supported
                cpu_.setReg(10, 0);
                cpu_.incrementPC();
                break;
            }
            
            // Find open file
            auto it = open_files_.find(fd);
            if (it == open_files_.end()) {
                // Invalid fd
                cpu_.setReg(10, static_cast<uint32_t>(-1));
                cpu_.incrementPC();
                break;
            }
            
            std::fstream *file = it->second;
            
            // Read into emulator memory
            uint32_t bytes_read = 0;
            for (uint32_t i = 0; i < count; ++i) {
                int c = file->get();
                if (c == EOF) break;
                
                memory_.write8(buf + i, static_cast<uint8_t>(c));
                bytes_read++;
            }
            
            // Return bytes read
            cpu_.setReg(10, bytes_read);
            cpu_.incrementPC();
            break;
        }
        
        case 57: { // close(fd)
            int fd = cpu_.getReg(10);  // a0 - file descriptor
            
            if (fd < 3) {
                // Can't close stdin/stdout/stderr
                cpu_.setReg(10, 0);  // Still return success
                cpu_.incrementPC();
                break;
            }
            
            // Find open file
            auto it = open_files_.find(fd);
            if (it == open_files_.end()) {
                // Invalid fd
                cpu_.setReg(10, static_cast<uint32_t>(-1));
                cpu_.incrementPC();
                break;
            }
            
            // Close and free
            it->second->close();
            delete it->second;
            open_files_.erase(it);
            
            // Return success
            cpu_.setReg(10, 0);
            cpu_.incrementPC();
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
    exit_code_ = 0;
    heap_break_ = 0x1000;
    mmap_regions_.clear();
    mmap_base_ = 0x10000;
    
    // Close all open files
    for (auto& pair : open_files_) {
        pair.second->close();
        delete pair.second;
    }
    open_files_.clear();
    next_fd_ = 3;
}
