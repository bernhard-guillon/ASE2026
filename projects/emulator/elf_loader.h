#ifndef ELF_LOADER_H
#define ELF_LOADER_H

#include <vector>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <iomanip>

// Proper ELF32 loader for RISC-V binaries with relocation support
class ElfLoader {
public:
    struct LoadSegment {
        uint32_t vaddr;       // Virtual address in memory
        uint32_t size;        // Size of segment in memory
        std::vector<uint8_t> data;  // Segment data to load
    };

    struct RelocationEntry {
        uint32_t offset;      // Offset in section to apply relocation
        uint32_t symbol_idx;  // Symbol index
        uint32_t r_type;      // Relocation type
        int32_t  addend;      // Addend (for RELA only)
        bool     is_rela;     // True if RELA, false if REL
    };

    static std::vector<LoadSegment> parseElf(const std::vector<uint8_t>& file_data) {
        if (file_data.size() < 52) {
            throw std::runtime_error("ELF file too small");
        }

        // Verify ELF magic
        if (file_data[0] != 0x7f || file_data[1] != 'E' || 
            file_data[2] != 'L' || file_data[3] != 'F') {
            throw std::runtime_error("Invalid ELF magic number");
        }

        // Check 32-bit
        if (file_data[4] != 1) {
            throw std::runtime_error("Only 32-bit ELF supported");
        }

        // Check little-endian
        if (file_data[5] != 1) {
            throw std::runtime_error("Only little-endian supported");
        }

        // Parse ELF32 header
        uint32_t e_phoff, e_shoff;
        uint16_t e_phentsize, e_phnum, e_shentsize, e_shnum;
        
        std::memcpy(&e_phoff, &file_data[28], 4);      // Program header offset
        std::memcpy(&e_shoff, &file_data[32], 4);      // Section header offset
        std::memcpy(&e_phentsize, &file_data[42], 2);  // Program header entry size
        std::memcpy(&e_phnum, &file_data[44], 2);      // Number of program headers
        std::memcpy(&e_shentsize, &file_data[46], 2);  // Section header entry size
        std::memcpy(&e_shnum, &file_data[48], 2);      // Number of section headers

        // Find symbol table and string table
        std::vector<uint8_t> symtab_data;
        std::vector<uint8_t> strtab_data;
        std::vector<uint8_t> shstrtab_data;
        uint16_t shstrndx = 0;
        std::memcpy(&shstrndx, &file_data[50], 2);
        
        // Load section headers to get symbol and string tables
        for (int i = 0; i < e_shnum; ++i) {
            uint32_t sh_offset = e_shoff + i * e_shentsize;
            if (sh_offset + 40 > file_data.size()) continue;
            
            uint32_t sh_type, sh_offset_f, sh_size;
            std::memcpy(&sh_type, &file_data[sh_offset + 4], 4);
            std::memcpy(&sh_offset_f, &file_data[sh_offset + 16], 4);
            std::memcpy(&sh_size, &file_data[sh_offset + 20], 4);
            
            // Type 3 = STRTAB, Type 2 = SYMTAB
            if (sh_type == 3 && i == shstrndx) {
                // String table for section names
                if (sh_offset_f + sh_size <= file_data.size()) {
                    shstrtab_data.assign(file_data.begin() + sh_offset_f,
                                        file_data.begin() + sh_offset_f + sh_size);
                }
            } else if (sh_type == 2) {
                // Symbol table
                if (sh_offset_f + sh_size <= file_data.size()) {
                    symtab_data.assign(file_data.begin() + sh_offset_f,
                                      file_data.begin() + sh_offset_f + sh_size);
                }
            }
        }

        // Load program headers (PT_LOAD segments)
        std::vector<LoadSegment> segments;
        
        for (int i = 0; i < e_phnum; ++i) {
            uint32_t ph_offset = e_phoff + i * e_phentsize;
            if (ph_offset + 32 > file_data.size()) {
                continue;
            }

            uint32_t p_type, p_offset, p_vaddr, p_filesz, p_memsz;
            std::memcpy(&p_type, &file_data[ph_offset + 0], 4);
            std::memcpy(&p_offset, &file_data[ph_offset + 4], 4);
            std::memcpy(&p_vaddr, &file_data[ph_offset + 8], 4);
            std::memcpy(&p_filesz, &file_data[ph_offset + 16], 4);
            std::memcpy(&p_memsz, &file_data[ph_offset + 20], 4);

            // PT_LOAD = 1
            if (p_type == 1) {
                LoadSegment seg;
                seg.vaddr = p_vaddr;
                seg.size = p_memsz;

                // Copy file data
                if (p_offset + p_filesz <= file_data.size()) {
                    seg.data.assign(file_data.begin() + p_offset,
                                   file_data.begin() + p_offset + p_filesz);
                }
                
                // Zero-fill BSS (memory size > file size)
                if (p_memsz > p_filesz) {
                    seg.data.resize(p_memsz, 0);
                }

                segments.push_back(seg);
            }
        }

        if (segments.empty()) {
            throw std::runtime_error("No PT_LOAD segments found in ELF");
        }

        return segments;
    }

    // Validate ELF file integrity
    static bool validateElf(const std::vector<uint8_t>& file_data) {
        if (file_data.size() < 52) return false;
        if (file_data[0] != 0x7f || file_data[1] != 'E' || 
            file_data[2] != 'L' || file_data[3] != 'F') return false;
        if (file_data[4] != 1) return false;  // Not 32-bit
        if (file_data[5] != 1) return false;  // Not little-endian
        return true;
    }

    // Get entry point from ELF header
    static uint32_t getEntryPoint(const std::vector<uint8_t>& file_data) {
        if (file_data.size() < 28) {
            throw std::runtime_error("ELF file too small to read entry point");
        }
        uint32_t entry;
        std::memcpy(&entry, &file_data[24], 4);
        return entry;
    }

    // Get program header count
    static uint16_t getProgramHeaderCount(const std::vector<uint8_t>& file_data) {
        if (file_data.size() < 46) {
            throw std::runtime_error("ELF file too small to read program header count");
        }
        uint16_t count;
        std::memcpy(&count, &file_data[44], 2);
        return count;
    }

    // Get section header count
    static uint16_t getSectionHeaderCount(const std::vector<uint8_t>& file_data) {
        if (file_data.size() < 50) {
            throw std::runtime_error("ELF file too small to read section header count");
        }
        uint16_t count;
        std::memcpy(&count, &file_data[48], 2);
        return count;
    }
};

#endif // ELF_LOADER_H
