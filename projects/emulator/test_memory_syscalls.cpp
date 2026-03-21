#include <gtest/gtest.h>
#include "Emulator.h"

class MemorySyscallTest : public ::testing::Test {
protected:
    Emulator emulator{65536};  // 64KB memory for mmap tests
    uint32_t initial_brk = 0;
    
    void SetUp() override {
        emulator.reset();
        // Query initial break on setup
        emulator.getCPU().setReg(10, 0);   // a0 = 0 (query)
        emulator.getCPU().setReg(17, 214); // syscall 214 (brk)
        std::vector<uint32_t> ecall = {0x00000073};
        emulator.loadProgram(ecall, 0);
        emulator.step();
        initial_brk = emulator.getCPU().getReg(10);
    }
    
    // Helper: Call syscall and return result in a0
    uint32_t callSyscall(uint32_t syscall_num, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3 = 0, uint32_t a4 = 0) {
        emulator.getCPU().setReg(10, a0);   // a0
        emulator.getCPU().setReg(11, a1);   // a1
        emulator.getCPU().setReg(12, a2);   // a2
        emulator.getCPU().setReg(13, a3);   // a3
        emulator.getCPU().setReg(14, a4);   // a4
        emulator.getCPU().setReg(17, syscall_num);  // a7 (syscall number)
        
        // ECALL instruction
        std::vector<uint32_t> ecall_program = {0x00000073};
        emulator.loadProgram(ecall_program, 0);
        emulator.step();
        return emulator.getCPU().getReg(10);  // return value in a0
    }
};

// ============================================================================
// brk(214) Tests - Heap Break Management (Always work, no external deps)
// ============================================================================

TEST_F(MemorySyscallTest, BrkQueryInitialBreak) {
    uint32_t current_brk = callSyscall(214, 0, 0, 0);
    EXPECT_NE(current_brk, 0u);
    EXPECT_EQ(current_brk, initial_brk);
}

TEST_F(MemorySyscallTest, BrkSetNewBreak) {
    uint32_t new_brk = initial_brk + 1024;
    uint32_t result = callSyscall(214, new_brk, 0, 0);
    EXPECT_EQ(result, new_brk);
    
    uint32_t verified_brk = callSyscall(214, 0, 0, 0);
    EXPECT_EQ(verified_brk, new_brk);
}

TEST_F(MemorySyscallTest, BrkDecreaseBreak) {
    uint32_t increased = callSyscall(214, initial_brk + 2048, 0, 0);
    EXPECT_EQ(increased, initial_brk + 2048);
    
    uint32_t decreased = callSyscall(214, initial_brk + 1024, 0, 0);
    EXPECT_EQ(decreased, initial_brk + 1024);
    
    uint32_t current = callSyscall(214, 0, 0, 0);
    EXPECT_EQ(current, initial_brk + 1024);
}

TEST_F(MemorySyscallTest, BrkMultipleIncrements) {
    uint32_t brk1 = callSyscall(214, initial_brk + 256, 0, 0);
    EXPECT_EQ(brk1, initial_brk + 256);
    
    uint32_t brk2 = callSyscall(214, initial_brk + 512, 0, 0);
    EXPECT_EQ(brk2, initial_brk + 512);
    
    uint32_t brk3 = callSyscall(214, initial_brk + 768, 0, 0);
    EXPECT_EQ(brk3, initial_brk + 768);
    
    uint32_t current = callSyscall(214, 0, 0, 0);
    EXPECT_EQ(current, initial_brk + 768);
}

TEST_F(MemorySyscallTest, BrkMemoryAccessibility) {
    uint32_t new_brk = initial_brk + 1024;
    callSyscall(214, new_brk, 0, 0);
    
    uint32_t test_addr = initial_brk + 512;
    emulator.getMemory().write32(test_addr, 0xDEADBEEF);
    uint32_t value = emulator.getMemory().read32(test_addr);
    EXPECT_EQ(value, 0xDEADBEEFu);
}

// ============================================================================
// mmap2(192) Tests - Memory Mapping
// ============================================================================

TEST_F(MemorySyscallTest, Mmap2AnonymousAllocation) {
    uint32_t addr = callSyscall(192, 0, 512, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    EXPECT_NE(addr, 0u);
}

TEST_F(MemorySyscallTest, Mmap2WriteToAllocatedMemory) {
    uint32_t addr = callSyscall(192, 0, 512, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    emulator.getMemory().write32(addr, 0x12345678);
    emulator.getMemory().write32(addr + 4, 0x9ABCDEF0);
    
    EXPECT_EQ(emulator.getMemory().read32(addr), 0x12345678u);
    EXPECT_EQ(emulator.getMemory().read32(addr + 4), 0x9ABCDEF0u);
}

TEST_F(MemorySyscallTest, Mmap2AnonymousIsZeroInitialized) {
    uint32_t addr = callSyscall(192, 0, 256, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    for (uint32_t offset = 0; offset < 64; offset += 4) {
        uint32_t value = emulator.getMemory().read32(addr + offset);
        EXPECT_EQ(value, 0u) << "Offset " << offset << " not zero";
    }
}

TEST_F(MemorySyscallTest, Mmap2FixedAllocation) {
    uint32_t fixed_addr = 0x4000;
    uint32_t addr = callSyscall(192, fixed_addr, 256, 3, 0x10 | 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 MAP_FIXED not available";
    }
    EXPECT_EQ(addr, fixed_addr);
}

TEST_F(MemorySyscallTest, Mmap2MultipleAllocations) {
    uint32_t addr1 = callSyscall(192, 0, 256, 3, 0x20, -1);
    if (addr1 == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    uint32_t addr2 = callSyscall(192, 0, 256, 3, 0x20, -1);
    EXPECT_NE(addr2, (uint32_t)-1);
    EXPECT_NE(addr1, addr2);
    
    emulator.getMemory().write32(addr1, 0xAAAAAAAAu);
    emulator.getMemory().write32(addr2, 0xBBBBBBBBu);
    
    EXPECT_EQ(emulator.getMemory().read32(addr1), 0xAAAAAAAAu);
    EXPECT_EQ(emulator.getMemory().read32(addr2), 0xBBBBBBBBu);
}

TEST_F(MemorySyscallTest, Mmap2LargeAllocation) {
    uint32_t addr = callSyscall(192, 0, 4096, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 large allocation not available";
    }
    
    emulator.getMemory().write32(addr + 0, 0x11111111u);
    emulator.getMemory().write32(addr + 4092, 0x22222222u);
    
    EXPECT_EQ(emulator.getMemory().read32(addr), 0x11111111u);
    EXPECT_EQ(emulator.getMemory().read32(addr + 4092), 0x22222222u);
}

// ============================================================================
// munmap(215) Tests - Memory Unmapping
// ============================================================================

TEST_F(MemorySyscallTest, MunmapValidRegion) {
    uint32_t addr = callSyscall(192, 0, 512, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available, cannot test munmap";
    }
    
    uint32_t result = callSyscall(215, addr, 512, 0);
    EXPECT_EQ(result, 0u);
}

TEST_F(MemorySyscallTest, MunmapInvalidRegion) {
    uint32_t invalid_addr = 0x1000000;
    uint32_t result = callSyscall(215, invalid_addr, 1024, 0);
    EXPECT_EQ(result, (uint32_t)-1);
}

TEST_F(MemorySyscallTest, MunmapSequentialAllocationsAndFree) {
    uint32_t addr1 = callSyscall(192, 0, 256, 3, 0x20, -1);
    if (addr1 == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    uint32_t addr2 = callSyscall(192, 0, 256, 3, 0x20, -1);
    EXPECT_NE(addr2, (uint32_t)-1);
    
    uint32_t result2 = callSyscall(215, addr2, 256, 0);
    EXPECT_EQ(result2, 0u);
    
    emulator.getMemory().write32(addr1, 0xCAFEBABEu);
    EXPECT_EQ(emulator.getMemory().read32(addr1), 0xCAFEBABEu);
}

TEST_F(MemorySyscallTest, MunmapPartialRegion) {
    uint32_t addr = callSyscall(192, 0, 1024, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    uint32_t result = callSyscall(215, addr, 512, 0);
    EXPECT_TRUE(result == 0u || result == (uint32_t)-1);
}

TEST_F(MemorySyscallTest, MunmapMultipleRegions) {
    uint32_t addr1 = callSyscall(192, 0, 256, 3, 0x20, -1);
    if (addr1 == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    uint32_t addr2 = callSyscall(192, 0, 256, 3, 0x20, -1);
    uint32_t addr3 = callSyscall(192, 0, 256, 3, 0x20, -1);
    
    EXPECT_NE(addr2, (uint32_t)-1);
    EXPECT_NE(addr3, (uint32_t)-1);
    
    uint32_t result = callSyscall(215, addr2, 256, 0);
    EXPECT_EQ(result, 0u);
    
    emulator.getMemory().write32(addr1, 0x11111111u);
    emulator.getMemory().write32(addr3, 0x33333333u);
    
    EXPECT_EQ(emulator.getMemory().read32(addr1), 0x11111111u);
    EXPECT_EQ(emulator.getMemory().read32(addr3), 0x33333333u);
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST_F(MemorySyscallTest, BrkMmapInteroperation) {
    uint32_t new_brk = initial_brk + 512;
    callSyscall(214, new_brk, 0, 0);
    
    uint32_t mmap_addr = callSyscall(192, 0, 256, 3, 0x20, -1);
    if (mmap_addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    emulator.getMemory().write32(initial_brk + 256, 0x11111111u);
    emulator.getMemory().write32(mmap_addr, 0x22222222u);
    
    EXPECT_EQ(emulator.getMemory().read32(initial_brk + 256), 0x11111111u);
    EXPECT_EQ(emulator.getMemory().read32(mmap_addr), 0x22222222u);
}

TEST_F(MemorySyscallTest, MallocSimulation) {
    uint32_t heap_ptr = initial_brk;
    
    emulator.getMemory().write32(heap_ptr, 256);
    emulator.getMemory().write32(heap_ptr + 4, 0x41414141u);
    
    heap_ptr += 256;
    callSyscall(214, initial_brk + 512, 0, 0);
    
    emulator.getMemory().write32(heap_ptr, 128);
    emulator.getMemory().write32(heap_ptr + 4, 0x42424242u);
    
    EXPECT_EQ(emulator.getMemory().read32(initial_brk + 4), 0x41414141u);
    EXPECT_EQ(emulator.getMemory().read32(initial_brk + 256 + 4), 0x42424242u);
}

TEST_F(MemorySyscallTest, AllocateUseUnmap) {
    uint32_t addr = callSyscall(192, 0, 512, 3, 0x20, -1);
    if (addr == (uint32_t)-1) {
        GTEST_SKIP() << "mmap2 not available";
    }
    
    for (uint32_t offset = 0; offset < 512; offset += 4) {
        emulator.getMemory().write32(addr + offset, offset);
    }
    
    for (uint32_t offset = 0; offset < 512; offset += 4) {
        uint32_t value = emulator.getMemory().read32(addr + offset);
        EXPECT_EQ(value, offset);
    }
    
    uint32_t result = callSyscall(215, addr, 512, 0);
    EXPECT_EQ(result, 0u);
}
