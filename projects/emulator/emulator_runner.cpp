#include <iostream>
#include <fstream>
#include <vector>
#include <cstring>
#include <termios.h>
#include <unistd.h>
#include <signal.h>
#include <csignal>
#include "Emulator.h"
#include "elf_loader.h"

// Global emulator pointer for signal handler
static Emulator* g_emulator = nullptr;
static volatile bool g_should_exit = false;

// Signal handler for Ctrl+C
void signal_handler(int signum) {
    if (signum == SIGINT) {
        g_should_exit = true;
        if (g_emulator) {
            std::cout << "\n\nInterrupt received. Exiting..." << std::endl;
        }
    }
}

// Enable raw terminal mode for keyboard input
struct TerminalMode {
    termios original_settings;
    
    TerminalMode() {
        tcgetattr(STDIN_FILENO, &original_settings);
        termios raw = original_settings;
        
        // Disable canonical mode and echo
        raw.c_lflag &= ~(ICANON | ECHO);
        raw.c_cc[VMIN] = 0;   // Non-blocking read
        raw.c_cc[VTIME] = 0;
        
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
    }
    
    ~TerminalMode() {
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_settings);
    }
};

// Process keyboard input in GUI mode
void process_gui_input(Emulator& emulator) {
    TerminalMode terminal;
    FramebufferRenderer renderer;
    signal(SIGINT, signal_handler);
    
    g_emulator = &emulator;
    g_should_exit = false;
    
    std::cout << "GUI mode active. Press any key to change character. Ctrl+C to exit." << std::endl;
    std::cout << "Starting with character code 0..." << std::endl;
    std::cout << std::endl;
    
    // Initial render with blank framebuffer
    renderer.render(emulator.getMemory());
    std::cout << "\nPress keys to change character:" << std::endl;
    
    bool first_key = true;
    while (!g_should_exit) {
        // Try to read a key without blocking
        unsigned char ch = 0;
        if (read(STDIN_FILENO, &ch, 1) == 1) {
            uint32_t key_code = static_cast<uint32_t>(ch);
            
            // Store ASCII code in register a0 (x10)
            emulator.getCPU().setReg(10, key_code);
            
            if (!first_key) {
                // Print key info (will be overwritten when framebuffer renders)
                if (key_code >= 32 && key_code < 127) {
                    std::cout << "Key: '" << ch << "' (ASCII " << key_code << ")" << std::endl;
                } else {
                    std::cout << "Key: (ASCII " << key_code << ")" << std::endl;
                }
            }
            first_key = false;
        }
        
        // Execute instructions per iteration (enough for framebuffer updates)
        for (int i = 0; i < 10000 && !g_should_exit; ++i) {
            try {
                emulator.step();
                if (emulator.isHalted()) {
                    g_should_exit = true;
                    break;
                }
            } catch (const std::exception& e) {
                // Ignore unsupported instructions during GUI mode
                // Program may be in a loop waiting for input
                break;
            }
        }
        
        // Render framebuffer to terminal
        renderer.render(emulator.getMemory());
        
        // Small sleep to prevent busy-waiting
        usleep(10000);  // 10ms
    }
    
    std::cout << "\nGUI mode closed." << std::endl;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <binary_file> [--gui] [--char <char>] [--verbose]" << std::endl;
        return 1;
    }
    
    bool verbose = false;
    bool gui_mode = false;
    uint32_t char_code = 0;
    const char* binary_file = argv[1];
    
    // Parse command-line arguments
    for (int i = 2; i < argc; ++i) {
        if (std::strcmp(argv[i], "--gui") == 0) {
            gui_mode = true;
        } else if (std::strcmp(argv[i], "--verbose") == 0 || std::strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (std::strcmp(argv[i], "--char") == 0) {
            if (i + 1 < argc) {
                // Extract ASCII code from character argument
                const char* char_arg = argv[i + 1];
                if (char_arg[0] != '\0') {
                    char_code = static_cast<unsigned char>(char_arg[0]);
                    if (verbose) {
                        std::cout << "Input character: '" << char_arg[0] << "' (ASCII " << char_code << ")" << std::endl;
                    }
                }
                ++i;  // Skip next argument since we consumed it
            } else {
                std::cerr << "Error: --char requires an argument" << std::endl;
                return 1;
            }
        }
    }
    
    // Read binary file
    std::ifstream file(binary_file, std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "Error: Could not open file " << binary_file << std::endl;
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
    
    // Create emulator with 1GB memory (for mmap and dynamic allocation)
    Emulator emulator(1024 * 1024 * 1024);
    
    // Parse and load ELF binary or raw binary
    try {
        // Check if it's an ELF file
        if (ElfLoader::validateElf(buffer)) {
            // Proper ELF loading
            auto segments = ElfLoader::parseElf(buffer);
            
            if (verbose) {
                std::cout << "Loaded ELF with " << segments.size() << " segment(s)" << std::endl;
            }
            
            // Load each segment into memory at its virtual address
            for (const auto& segment : segments) {
                if (verbose) {
                    std::cout << "  Loading segment at 0x" << std::hex << segment.vaddr 
                              << " size 0x" << segment.size << std::dec << std::endl;
                }
                
                for (size_t i = 0; i < segment.data.size(); ++i) {
                    emulator.getMemory().write8(segment.vaddr + i, segment.data[i]);
                }
                
                // Zero-fill remaining BSS if needed
                for (size_t i = segment.data.size(); i < segment.size; ++i) {
                    emulator.getMemory().write8(segment.vaddr + i, 0);
                }
            }
            
            // Get entry point from ELF header
            uint32_t entry_point = ElfLoader::getEntryPoint(buffer);
            emulator.getCPU().setPC(entry_point);
            
            if (verbose) {
                std::cout << "Entry point: 0x" << std::hex << entry_point << std::dec << std::endl;
            }
        } else {
            // Fallback to raw binary loading for backward compatibility
            if (verbose) {
                std::cout << "Not an ELF file, loading as raw binary at address 0" << std::endl;
            }
            
            for (size_t i = 0; i < buffer.size(); ++i) {
                emulator.getMemory().write8(i, buffer[i]);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Error loading binary: " << e.what() << std::endl;
        return 1;
    }
    
    // Initialize stack pointer to 512MB (high in address space for stack growth)
    emulator.getCPU().setReg(2, 512 * 1024 * 1024);
    
    // Set register x10 (a0, first function argument) with character code if provided (non-GUI mode)
    if (!gui_mode && char_code > 0) {
        emulator.getCPU().setReg(10, char_code);
    } else if (gui_mode && char_code == 0) {
        // In GUI mode, initialize with space character
        emulator.getCPU().setReg(10, 32);
    }
    
    if (verbose) {
        std::cout << "Program loaded at address 0" << std::endl;
        if (gui_mode) {
            std::cout << "Running in GUI mode" << std::endl;
        } else if (char_code > 0) {
            std::cout << "Register x10 (a0) set to " << char_code << std::endl;
        }
        std::cout << "Starting execution..." << std::endl;
        if (!gui_mode) {
            std::cout << "----------------------------------------" << std::endl;
        }
    }
    
    // Run the program
    try {
        if (gui_mode) {
            // Interactive GUI mode
            process_gui_input(emulator);
        } else {
            // Standard single-execution mode
            emulator.run(1000000);  // Max 1M instructions (for recursive functions)
            
            if (verbose) {
                std::cout << "----------------------------------------" << std::endl;
                if (emulator.isHalted()) {
                    std::cout << "Program exited normally" << std::endl;
                } else {
                    std::cout << "Program reached instruction limit" << std::endl;
                }
                std::cout << "Final PC: 0x" << std::hex << emulator.getCPU().getPC() << std::endl;
            }
        }
        
        // Return the program's exit code
        return emulator.getExitCode();
        
    } catch (const std::exception& e) {
        std::cerr << "Error during execution: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}

