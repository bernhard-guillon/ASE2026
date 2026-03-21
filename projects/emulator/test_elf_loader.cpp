#include <gtest/gtest.h>
#include <fstream>
#include <vector>
#include "elf_loader.h"

// Helper function to load ELF file
std::vector<uint8_t> loadFile(const std::string& filename) {
    // Try current directory first, then known build subdirectories, then project root
    std::vector<std::string> paths = {
        filename,
        "elf_loader_tests/" + filename,
#ifdef ELF_LOADER_BUILD_DIR
        std::string(ELF_LOADER_BUILD_DIR) + "/" + filename,
#endif
        "../" + filename,
        "../../" + filename,
    };
    
    for (const auto& path : paths) {
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        if (file) {
            std::streamsize size = file.tellg();
            file.seekg(0, std::ios::beg);
            std::vector<uint8_t> buffer(size);
            if (file.read(reinterpret_cast<char*>(buffer.data()), size)) {
                return buffer;
            }
        }
    }
    
    throw std::runtime_error("Could not open file: " + filename);
}

// Test ELF validation
class ElfLoaderTest : public ::testing::Test {
protected:
    std::vector<uint8_t> simple_elf;
    std::vector<uint8_t> with_rodata_elf;
    
    virtual void SetUp() {
        try {
            simple_elf = loadFile("test_nop_loop.elf");
            with_rodata_elf = loadFile("test_rodata_read.elf");
        } catch (const std::exception& e) {
            GTEST_SKIP() << "ELF test files not found: " << e.what();
        }
    }
};

// Test 1: ELF magic validation
TEST_F(ElfLoaderTest, ValidateElfMagic) {
    EXPECT_TRUE(ElfLoader::validateElf(simple_elf));
    EXPECT_TRUE(ElfLoader::validateElf(with_rodata_elf));
}

// Test 2: Invalid magic should fail
TEST_F(ElfLoaderTest, InvalidMagic) {
    std::vector<uint8_t> bad_magic = {0x00, 0x00, 0x00, 0x00};
    EXPECT_FALSE(ElfLoader::validateElf(bad_magic));
}

// Test 3: Too small file should fail
TEST_F(ElfLoaderTest, FileTooSmall) {
    std::vector<uint8_t> tiny = {0x7f, 0x45, 0x4c, 0x46};
    EXPECT_FALSE(ElfLoader::validateElf(tiny));
}

// Test 4: Parse valid ELF
TEST_F(ElfLoaderTest, ParseValidElf) {
    EXPECT_NO_THROW({
        auto segments = ElfLoader::parseElf(simple_elf);
        EXPECT_GT(segments.size(), 0);
    });
}

// Test 5: Segments have correct properties
TEST_F(ElfLoaderTest, SegmentProperties) {
    auto segments = ElfLoader::parseElf(simple_elf);
    
    for (const auto& seg : segments) {
        EXPECT_GT(seg.size, 0);
        EXPECT_LE(seg.data.size(), seg.size);
        // VMA should not be huge (sanity check)
        EXPECT_LT(seg.vaddr, 1024 * 1024);
    }
}

// Test 6: Get entry point
TEST_F(ElfLoaderTest, GetEntryPoint) {
    uint32_t entry = ElfLoader::getEntryPoint(simple_elf);
    // Entry point should be in loaded segment range
    EXPECT_LT(entry, 1024 * 1024);
}

// Test 7: Program header count
TEST_F(ElfLoaderTest, GetProgramHeaderCount) {
    uint16_t count = ElfLoader::getProgramHeaderCount(simple_elf);
    EXPECT_GT(count, 0);
    EXPECT_LT(count, 100);  // Sanity check
}

// Test 8: Section header count
TEST_F(ElfLoaderTest, GetSectionHeaderCount) {
    uint16_t count = ElfLoader::getSectionHeaderCount(simple_elf);
    EXPECT_GT(count, 0);
    EXPECT_LT(count, 100);  // Sanity check
}

// Test 9: ELF with .rodata section
TEST_F(ElfLoaderTest, RodataSegment) {
    auto segments = ElfLoader::parseElf(with_rodata_elf);
    
    // Should have at least one segment
    EXPECT_GT(segments.size(), 0);
    
    // Total size should be substantial (includes .rodata)
    size_t total_size = 0;
    for (const auto& seg : segments) {
        total_size += seg.size;
    }
    EXPECT_GT(total_size, 100);
}

// Test 10: Data integrity - segment data should match expected size
TEST_F(ElfLoaderTest, SegmentDataIntegrity) {
    auto segments = ElfLoader::parseElf(simple_elf);
    
    for (const auto& seg : segments) {
        // Data size should be <= memory size
        EXPECT_LE(seg.data.size(), seg.size);
        
        // Data should not be empty
        EXPECT_GT(seg.data.size(), 0);
    }
}

// Test 11: Multiple segments handled correctly
TEST_F(ElfLoaderTest, MultipleSegments) {
    auto segments = ElfLoader::parseElf(with_rodata_elf);
    
    // Check that segments don't overlap
    for (size_t i = 0; i < segments.size(); ++i) {
        uint32_t seg1_start = segments[i].vaddr;
        uint32_t seg1_end = segments[i].vaddr + segments[i].size;
        
        for (size_t j = i + 1; j < segments.size(); ++j) {
            uint32_t seg2_start = segments[j].vaddr;
            uint32_t seg2_end = segments[j].vaddr + segments[j].size;
            
            // Segments should not overlap
            EXPECT_FALSE(
                (seg1_start < seg2_end && seg1_end > seg2_start)
            ) << "Segment " << i << " overlaps with segment " << j;
        }
    }
}

// Test 12: Parse ELF with invalid segment size should not crash
TEST_F(ElfLoaderTest, GracefulErrorHandling) {
    std::vector<uint8_t> corrupted = simple_elf;
    // Corrupt a field
    if (corrupted.size() > 50) {
        corrupted[48] = 255;  // Set invalid section count
    }
    
    // Should not crash, might throw
    try {
        ElfLoader::parseElf(corrupted);
        // If it succeeds, that's also OK
    } catch (const std::exception&) {
        // Expected behavior
    }
}

// Test 13: Entry point from valid ELF is reasonable
TEST_F(ElfLoaderTest, EntryPointReasonable) {
    uint32_t entry = ElfLoader::getEntryPoint(simple_elf);
    
    // Entry point should be within typical program space
    EXPECT_LT(entry, 100 * 1024 * 1024);  // Less than 100MB
}

// Test 14: Validate ELF with correct structure
TEST_F(ElfLoaderTest, ValidateStructure) {
    EXPECT_TRUE(ElfLoader::validateElf(simple_elf));
    
    // Check that we can read header fields without exceptions
    EXPECT_NO_THROW({
        ElfLoader::getEntryPoint(simple_elf);
        ElfLoader::getProgramHeaderCount(simple_elf);
        ElfLoader::getSectionHeaderCount(simple_elf);
    });
}

// Test 15: Empty .rodata section handling
TEST_F(ElfLoaderTest, EmptyRodataHandling) {
    // Parse ELF with .rodata
    auto segments = ElfLoader::parseElf(with_rodata_elf);
    
    // Should still parse successfully even with large sections
    EXPECT_GT(segments.size(), 0);
    
    // Find segment with largest size
    size_t max_size = 0;
    for (const auto& seg : segments) {
        max_size = std::max(max_size, (size_t)seg.size);
    }
    EXPECT_GT(max_size, 0);
}
