#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <iomanip>
#include <limits>
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
void process_gui_input(Emulator& emulator, uint32_t cycles_per_frame) {
    TerminalMode terminal;
    FramebufferRenderer renderer;
    signal(SIGINT, signal_handler);
    
    g_emulator = &emulator;
    g_should_exit = false;
    
    std::cout << "GUI mode active. Keys switch character; auto-advance runs continuously. Ctrl+C to exit." << std::endl;
    std::cout << std::endl;
    
    // Initial render
    renderer.render(emulator.getMemory());
    
    while (!g_should_exit) {
        // Try to read a key without blocking
        unsigned char ch = 0;
        bool key_pressed = false;
        if (read(STDIN_FILENO, &ch, 1) == 1) {
            uint32_t key_code = static_cast<uint32_t>(ch);
            
            // Store key in registers and memory-mapped 0x154004
            emulator.getCPU().setReg(10, key_code);
            emulator.getCPU().setReg(9, key_code);
            emulator.getMemory().write32(0x154004, key_code);
            
            if (key_code >= 32 && key_code < 127) {
                std::cout << "Key: '" << static_cast<char>(key_code) << "' (ASCII " << key_code << ")" << std::endl;
            } else {
                std::cout << "Key: (ASCII " << key_code << ")" << std::endl;
            }
            key_pressed = true;
        }
        
        // Always run inference — enables auto-advance for models with MODEL_HAS_DONE_FLAG
        emulator.getMemory().write32(0x154000, 0);
        for (uint32_t i = 0; i < cycles_per_frame && !g_should_exit; ++i) {
            try {
                emulator.step();
                if (emulator.isHalted()) {
                    g_should_exit = true;
                    break;
                }
                if (emulator.getMemory().read32(0x154000) == 1) {
                    break;
                }
            } catch (const std::exception& e) {
                break;
            }
        }
        
        if (key_pressed) {
            // Read framebuffer to find current position
            uint32_t max_brightness = 0;
            uint32_t current_state = 0;
            for (uint32_t i = 0; i < 400; ++i) {
                uint8_t pixel = emulator.getMemory().read8(0x20000 + i);
                if (pixel > max_brightness) {
                    max_brightness = pixel;
                    current_state = i;
                }
            }
            if (max_brightness > 0) {
                std::cout << "  Position: " << current_state;
                std::cout << " (x:" << (current_state % 20) << ", y:" << (current_state / 20) << ")" << std::endl;
            }
        }
        
        // Render framebuffer to terminal
        renderer.render(emulator.getMemory());
        
        // Sleep controls auto-advance speed; ~150ms = ~6 fps
        usleep(150000);  // 150ms
    }
    
    std::cout << "\nGUI mode closed." << std::endl;
}

// Process keyboard input for interactive movement mode
void process_movement_input(Emulator& emulator) {
    TerminalMode terminal;
    FramebufferRenderer renderer;
    signal(SIGINT, signal_handler);
    
    g_emulator = &emulator;
    g_should_exit = false;
    
    std::cout << "Movement mode active. Use hjkl to move, 'q' to quit." << std::endl;
    std::cout << "h: left, j: down, k: up, l: right, space: stay" << std::endl;
    std::cout << std::endl;
    
    uint32_t current_state = 200;
    bool waiting_for_prediction = false;
    
    while (!g_should_exit) {
        // Read key
        unsigned char ch = 0;
        if (read(STDIN_FILENO, &ch, 1) == 1) {
            if (ch == 'q') {
                g_should_exit = true;
                break;
            }
            
            // Send raw keycode to firmware (firmware handles mapping + state tracking)
            emulator.getCPU().setReg(10, static_cast<uint32_t>(ch));
            emulator.getCPU().setReg(9, static_cast<uint32_t>(ch));
            emulator.getMemory().write32(0x154004, static_cast<uint32_t>(ch));
            waiting_for_prediction = true;
            
            std::cout << "Key: '" << ch << "' (waiting for neural prediction)" << std::endl;
        }
        
        if (waiting_for_prediction) {
            // Run until firmware completes one iteration (or timeout)
            emulator.getMemory().write32(0x154000, 0);
            for (int i = 0; i < 10000000 && !g_should_exit; ++i) {
                try {
                    emulator.step();
                    if (emulator.isHalted()) {
                        g_should_exit = true;
                        break;
                    }
                    if (emulator.getMemory().read32(0x154000) == 1) {
                        break;
                    }
                } catch (const std::exception& e) {
                    break;
                }
            }
            
            // Read framebuffer to find current position
            uint32_t max_brightness = 0;
            for (uint32_t i = 0; i < 400; ++i) {
                uint8_t pixel = emulator.getMemory().read8(0x20000 + i);
                if (pixel > max_brightness) {
                    max_brightness = pixel;
                    current_state = i;
                }
            }
            
            if (max_brightness > 0) {
                std::cout << "Neural prediction: moved to " << current_state;
                std::cout << " (x:" << (current_state % 20) << ", y:" << (current_state / 20) << ")" << std::endl;
            }
            waiting_for_prediction = false;
        }
        
        // Render framebuffer to terminal
        renderer.render(emulator.getMemory());
        
        // Small sleep to prevent busy-waiting
        usleep(50000);  // 50ms for smoother movement
    }
    
    std::cout << "\nMovement mode closed." << std::endl;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <binary_file> [--gui] [--movement] [--char <char>] [--char-code <uint32>] [--cycles <count>] [--gui-cycles <count>] [--render-framebuffer] [--dump-framebuffer] [--verbose]" << std::endl;
        return 1;
    }
    
    bool verbose = false;
    bool gui_mode = false;
    bool movement_mode = false;
    bool render_fb = false;
    bool dump_fb = false;
    bool char_specified = false;
    uint32_t char_code = 0;
    uint32_t max_cycles = 1000000;  // Default 1M cycles
    uint32_t gui_cycles = 50000;    // Default 50K cycles per frame for GUI
    const char* binary_file = argv[1];
    
    struct DumpRegion {
        uint32_t addr;
        uint32_t count;
    };
    std::vector<DumpRegion> dump_regions;
    
    // Parse command-line arguments
    for (int i = 2; i < argc; ++i) {
        if (std::strcmp(argv[i], "--gui") == 0) {
            gui_mode = true;
        } else if (std::strcmp(argv[i], "--movement") == 0) {
            movement_mode = true;
        } else if (std::strcmp(argv[i], "--verbose") == 0 || std::strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (std::strcmp(argv[i], "--render-framebuffer") == 0) {
            render_fb = true;
        } else if (std::strcmp(argv[i], "--dump-framebuffer") == 0) {
            dump_fb = true;
        } else if (std::strcmp(argv[i], "--char") == 0) {
            if (i + 1 < argc) {
                // Extract ASCII code from character argument
                const char* char_arg = argv[i + 1];
                if (char_arg[0] != '\0') {
                    char_specified = true;
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
        } else if (std::strcmp(argv[i], "--char-code") == 0) {
            if (i + 1 < argc) {
                char* end = nullptr;
                unsigned long long parsed = std::strtoull(argv[i + 1], &end, 0);
                if (end == argv[i + 1] || *end != '\0' ||
                    parsed > static_cast<unsigned long long>(std::numeric_limits<uint32_t>::max())) {
                    std::cerr << "Error: --char-code must be an integer in [0, 4294967295]" << std::endl;
                    return 1;
                }
                char_specified = true;
                char_code = static_cast<uint32_t>(parsed);
                if (verbose) {
                    std::cout << "Input character code: " << char_code << std::endl;
                }
                ++i;  // Skip next argument
            } else {
                std::cerr << "Error: --char-code requires a number" << std::endl;
                return 1;
            }
        } else if (std::strcmp(argv[i], "--cycles") == 0) {
            if (i + 1 < argc) {
                max_cycles = std::atoi(argv[i + 1]);
                if (verbose) {
                    std::cout << "Max cycles set to: " << max_cycles << std::endl;
                }
                ++i;  // Skip next argument
            } else {
                std::cerr << "Error: --cycles requires a number" << std::endl;
                return 1;
            }
        } else if (std::strcmp(argv[i], "--gui-cycles") == 0) {
            if (i + 1 < argc) {
                gui_cycles = std::atoi(argv[i + 1]);
                if (verbose) {
                    std::cout << "GUI cycles per frame set to: " << gui_cycles << std::endl;
                }
                ++i;  // Skip next argument
            } else {
                std::cerr << "Error: --gui-cycles requires a number" << std::endl;
                return 1;
            }
        } else if (std::strcmp(argv[i], "--dump-memory") == 0) {
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
    
    std::string binary_path = binary_file;

    // Set register x10 (a0, first function argument) with character code if provided
    bool is_counter_char_model = binary_path.find("counter-char") != std::string::npos;
    bool is_squash_model = binary_path.find("squash") != std::string::npos;

    if (char_specified) {
        // Use provided character code
        emulator.getCPU().setReg(10, char_code);
        emulator.getMemory().write32(0x154004, char_code);
    } else if (gui_mode) {
        // Counter/char demos should start on 'a' so the first rendered frame
        // matches the standalone character generator. Squash game needs 0 for no input.
        if (is_counter_char_model) {
            emulator.getCPU().setReg(10, 97);
        } else if (is_squash_model) {
            emulator.getCPU().setReg(10, 0);
            emulator.getMemory().write32(0x154004, 0);
        } else {
            emulator.getCPU().setReg(10, 32);
        }
    }
    
    if (verbose) {
        std::cout << "Program loaded at address 0" << std::endl;
        if (gui_mode) {
            std::cout << "Running in GUI mode" << std::endl;
        } else if (char_specified) {
            std::cout << "Register x10 (a0) set to " << char_code << std::endl;
        }
        std::cout << "Starting execution..." << std::endl;
        if (!gui_mode) {
            std::cout << "----------------------------------------" << std::endl;
        }
    }
    
    // Run the program
    try {
        if (movement_mode) {
            // Interactive movement mode
            process_movement_input(emulator);
        } else if (gui_mode) {
            // Interactive GUI mode
            process_gui_input(emulator, gui_cycles);
        } else {
            // Standard single-execution mode
            uint32_t executed_cycles = 0;
            for (; executed_cycles < max_cycles && !emulator.isHalted(); ++executed_cycles) {
                emulator.step();
            }
            
            if (verbose) {
                std::cout << "----------------------------------------" << std::endl;
                if (emulator.isHalted()) {
                    std::cout << "Program exited normally" << std::endl;
                } else {
                    std::cout << "Program reached instruction limit" << std::endl;
                }
                std::cout << "Cycles: " << executed_cycles << std::endl;
                std::cout << "Final PC: 0x" << std::hex << emulator.getCPU().getPC() << std::endl;
            }
        }
        
        if (dump_fb) {
            std::ios::fmtflags old_flags = std::cout.flags();
            char old_fill = std::cout.fill();
            std::cout << "FRAMEBUFFER_HEX:";
            for (uint32_t i = 0; i < 400; ++i) {
                uint8_t v = emulator.getMemory().read8(0x20000 + i);
                std::cout << std::hex << std::setw(2) << std::setfill('0')
                          << static_cast<unsigned>(v);
            }
            std::cout.flags(old_flags);
            std::cout.fill(old_fill);
            std::cout << std::endl;
        }

        // Render framebuffer if requested
        if (render_fb) {
            FramebufferRenderer renderer;
            renderer.render(emulator.getMemory());
        }
        
        // Dump memory regions
        for (const auto& region : dump_regions) {
            emulator.dumpMemory(region.addr, region.count);
        }
        
        // Return the program's exit code
        return emulator.getExitCode();
        
    } catch (const std::exception& e) {
        std::cerr << "Error during execution: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
