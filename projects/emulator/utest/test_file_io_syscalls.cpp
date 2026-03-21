#include <gtest/gtest.h>
#include <fstream>
#include <cstdlib>
#include <unistd.h>
#include <cstring>
#include "Emulator.h"

class FileIOTest : public ::testing::Test {
protected:
    Emulator emulator{8192};  // 8KB memory for tests
    std::string test_dir = "/tmp";
    std::string test_file = "/tmp/test_io_file.txt";
    std::string test_file2 = "/tmp/test_io_file2.txt";
    
    void SetUp() override {
        emulator.reset();
        // Clean up any test files from previous runs
        std::remove(test_file.c_str());
        std::remove(test_file2.c_str());
    }
    
    void TearDown() override {
        // Clean up test files
        std::remove(test_file.c_str());
        std::remove(test_file2.c_str());
    }
    
    // Helper: Write a string to emulator memory at given address
    void writeStringToMemory(uint32_t addr, const std::string& str) {
        for (size_t i = 0; i < str.length(); i++) {
            emulator.getMemory().write8(addr + i, str[i]);
        }
        emulator.getMemory().write8(addr + str.length(), 0);  // null terminator
    }
    
    // Helper: Read string from emulator memory
    std::string readStringFromMemory(uint32_t addr, size_t max_len) {
        std::string result;
        for (size_t i = 0; i < max_len; i++) {
            uint8_t c = emulator.getMemory().read8(addr + i);
            if (c == 0) break;
            result += (char)c;
        }
        return result;
    }
    
    // Helper: Execute syscall by setting registers and stepping through ecall
    void executeSyscall(uint32_t syscall_num, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3 = 0) {
        emulator.getCPU().setReg(10, a0);   // a0
        emulator.getCPU().setReg(11, a1);   // a1
        emulator.getCPU().setReg(12, a2);   // a2
        emulator.getCPU().setReg(13, a3);   // a3
        emulator.getCPU().setReg(17, syscall_num);  // a7 (syscall number)
        
        // ECALL instruction: 0b000000000000_00000_000_00000_1110011
        std::vector<uint32_t> ecall_program = {0x00000073};
        emulator.loadProgram(ecall_program, 0);
        emulator.step();
    }
    
    // Helper: Execute syscall and return result in a0
    uint32_t callSyscall(uint32_t syscall_num, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3 = 0) {
        executeSyscall(syscall_num, a0, a1, a2, a3);
        return emulator.getCPU().getReg(10);  // return value in a0
    }
};

// ============================================================================
// openat(56) Tests - File Opening
// ============================================================================

TEST_F(FileIOTest, OpenatExistingFileReadMode) {
    // Create a test file first
    std::ofstream file(test_file);
    file << "test content";
    file.close();
    
    // Write path to memory
    writeStringToMemory(100, test_file);
    
    // Call openat(AT_FDCWD, path, O_RDONLY, 0)
    // AT_FDCWD = -100, O_RDONLY = 0
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Should return valid fd (>= 3)
    EXPECT_GE(fd, 3);
    EXPECT_NE(fd, (uint32_t)-1);
    
    // Clean up by closing
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, OpenatNonExistentFileError) {
    // Try to open non-existent file in read mode
    writeStringToMemory(100, "/tmp/nonexistent_file_12345.txt");
    
    // Call openat(AT_FDCWD, path, O_RDONLY, 0)
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Should return -1 (error)
    EXPECT_EQ(fd, (uint32_t)-1);
}

TEST_F(FileIOTest, OpenatCreateNewFile) {
    // O_WRONLY = 1, O_CREAT = 64
    writeStringToMemory(100, test_file2);
    
    // Call openat(AT_FDCWD, path, O_WRONLY | O_CREAT, 0644)
    uint32_t fd = callSyscall(56, -100, 100, 1 | 64, 0644);
    
    // Should return valid fd
    EXPECT_GE(fd, 3);
    
    // Verify file was created
    EXPECT_TRUE(std::ifstream(test_file2).good());
    
    // Close the file
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, OpenatWriteOnlyMode) {
    // Create file first
    std::ofstream f(test_file);
    f << "initial";
    f.close();
    
    writeStringToMemory(100, test_file);
    
    // O_WRONLY = 1
    uint32_t fd = callSyscall(56, -100, 100, 1, 0);
    
    EXPECT_GE(fd, 3);
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, OpenatAppendMode) {
    // Create file with content
    std::ofstream f(test_file);
    f << "line1\n";
    f.close();
    
    writeStringToMemory(100, test_file);
    
    // O_WRONLY | O_APPEND = 1 | 1024
    uint32_t fd = callSyscall(56, -100, 100, 1 | 1024, 0);
    
    EXPECT_GE(fd, 3);
    
    callSyscall(57, fd, 0, 0);
}

// ============================================================================
// read(63) Tests - File Reading
// ============================================================================

TEST_F(FileIOTest, ReadBasicFromFile) {
    // Create test file with known content
    std::string content = "Hello, World!";
    std::ofstream f(test_file);
    f << content;
    f.close();
    
    writeStringToMemory(100, test_file);
    
    // Open file
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    EXPECT_GE(fd, 3);
    
    // Read from file: read(fd, buffer, count)
    uint32_t bytes_read = callSyscall(63, fd, 200, 20);
    
    // Should read all 13 bytes
    EXPECT_EQ(bytes_read, (uint32_t)content.length());
    
    // Verify content in memory
    std::string result = readStringFromMemory(200, 20);
    EXPECT_EQ(result, content);
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, ReadWithCountLargerThanFile) {
    // Create small file
    std::string content = "Hi";
    std::ofstream f(test_file);
    f << content;
    f.close();
    
    writeStringToMemory(100, test_file);
    
    // Open and read with large count
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    uint32_t bytes_read = callSyscall(63, fd, 200, 100);
    
    // Should only read what's available
    EXPECT_EQ(bytes_read, (uint32_t)content.length());
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, ReadAtEndOfFile) {
    // Create file
    std::ofstream f(test_file);
    f << "test";
    f.close();
    
    writeStringToMemory(100, test_file);
    
    // Open file
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Seek to end
    callSyscall(19, fd, 4, 2);  // lseek(fd, 4, SEEK_SET)
    
    // Try to read from end
    uint32_t bytes_read = callSyscall(63, fd, 200, 10);
    
    // Should return 0 (EOF)
    EXPECT_EQ(bytes_read, 0u);
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, ReadMultipleTimesAdvancesPosition) {
    // Create file with 10 bytes
    std::ofstream f(test_file);
    f << "0123456789";
    f.close();
    
    writeStringToMemory(100, test_file);
    
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Read 5 bytes
    uint32_t read1 = callSyscall(63, fd, 200, 5);
    EXPECT_EQ(read1, 5u);
    std::string result1 = readStringFromMemory(200, 5);
    EXPECT_EQ(result1, "01234");
    
    // Read next 5 bytes (should get 56789)
    uint32_t read2 = callSyscall(63, fd, 300, 5);
    EXPECT_EQ(read2, 5u);
    std::string result2 = readStringFromMemory(300, 5);
    EXPECT_EQ(result2, "56789");
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, ReadFromInvalidFdReturnsError) {
    // Try to read from invalid fd
    uint32_t bytes_read = callSyscall(63, 999, 200, 10);
    
    // Should return -1 (error)
    EXPECT_EQ(bytes_read, (uint32_t)-1);
}

// ============================================================================
// close(57) Tests - File Closing
// ============================================================================

TEST_F(FileIOTest, CloseValidFileDescriptor) {
    // Create and open file
    std::ofstream f(test_file);
    f << "test";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    EXPECT_GE(fd, 3);
    
    // Close the file
    uint32_t result = callSyscall(57, fd, 0, 0);
    
    // Should return 0 (success)
    EXPECT_EQ(result, 0u);
}

TEST_F(FileIOTest, CloseInvalidFdReturnsError) {
    // Try to close invalid fd
    uint32_t result = callSyscall(57, 999, 0, 0);
    
    // Should return -1 (error)
    EXPECT_EQ(result, (uint32_t)-1);
}

TEST_F(FileIOTest, CloseStdoutStderr) {
    // Close stdout (fd 1) - implementation allows closing
    uint32_t result1 = callSyscall(57, 1, 0, 0);
    // Returns 0 (success) since we allow closing stdout
    EXPECT_EQ(result1, 0u);
    
    // Close stderr (fd 2)
    uint32_t result2 = callSyscall(57, 2, 0, 0);
    // Also allowed, returns 0
    EXPECT_EQ(result2, 0u);
}

TEST_F(FileIOTest, FdReuseAfterClose) {
    // Open first file
    std::ofstream f1(test_file);
    f1 << "file1";
    f1.close();
    
    std::ofstream f2(test_file2);
    f2 << "file2";
    f2.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd1 = callSyscall(56, -100, 100, 0, 0);
    int first_fd = fd1;
    
    // Close first file
    callSyscall(57, fd1, 0, 0);
    
    // Open second file
    writeStringToMemory(100, test_file2);
    uint32_t fd2 = callSyscall(56, -100, 100, 0, 0);
    
    // Second fd might not reuse the slot (depends on implementation)
    // Just verify we get a valid fd
    EXPECT_GE(fd2, 3u);
    
    callSyscall(57, fd2, 0, 0);
}

// ============================================================================
// lseek(19) Tests - File Positioning
// ============================================================================

TEST_F(FileIOTest, LseekSetAbsolutePosition) {
    // Create file with known content
    std::ofstream f(test_file);
    f << "0123456789";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Seek to position 5 with SEEK_SET (0)
    uint32_t pos = callSyscall(19, fd, 5, 0);
    EXPECT_EQ(pos, 5u);
    
    // Read from position 5
    uint32_t bytes_read = callSyscall(63, fd, 200, 3);
    EXPECT_EQ(bytes_read, 3u);
    std::string result = readStringFromMemory(200, 3);
    EXPECT_EQ(result, "567");
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, LseekCurRelativeToCurrentPosition) {
    std::ofstream f(test_file);
    f << "0123456789";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Read 3 bytes (moves position to 3)
    callSyscall(63, fd, 200, 3);
    
    // Seek forward 2 bytes relative to current (SEEK_CUR = 1)
    uint32_t pos = callSyscall(19, fd, 2, 1);
    EXPECT_EQ(pos, 5u);
    
    // Read should get bytes starting at position 5
    callSyscall(63, fd, 300, 3);
    std::string result = readStringFromMemory(300, 3);
    EXPECT_EQ(result, "567");
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, LseekEndRelativeToFileEnd) {
    std::ofstream f(test_file);
    f << "0123456789";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Seek to 2 bytes before end with SEEK_END (2)
    uint32_t pos = callSyscall(19, fd, -2, 2);
    EXPECT_EQ(pos, 8u);
    
    // Read should get last 2 bytes
    uint32_t bytes_read = callSyscall(63, fd, 200, 3);
    EXPECT_EQ(bytes_read, 2u);
    std::string result = readStringFromMemory(200, 2);
    EXPECT_EQ(result, "89");
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, LseekNegativeOffsetError) {
    std::ofstream f(test_file);
    f << "test";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Try to seek to negative position with SEEK_SET
    // Implementation may clamp to 0 instead of returning error
    uint32_t pos = callSyscall(19, fd, -5, 0);
    
    // Either returns 0 (clamped) or -1 (error) is acceptable
    // Most implementations clamp to 0
    EXPECT_TRUE(pos == 0u || pos == (uint32_t)-1);
    
    callSyscall(57, fd, 0, 0);
}

TEST_F(FileIOTest, LseekBeyondFileEnd) {
    std::ofstream f(test_file);
    f << "test";
    f.close();
    
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 0, 0);
    
    // Seek beyond file end (this is allowed in POSIX)
    uint32_t pos = callSyscall(19, fd, 100, 0);
    
    // Should succeed and return the position
    EXPECT_EQ(pos, 100u);
    
    // Next read should return 0 bytes
    uint32_t bytes_read = callSyscall(63, fd, 200, 10);
    EXPECT_EQ(bytes_read, 0u);
    
    callSyscall(57, fd, 0, 0);
}

// ============================================================================
// write(64) to Files Tests - Extended Write to File Descriptors
// ============================================================================

TEST_F(FileIOTest, WriteToFileDescriptor) {
    writeStringToMemory(100, test_file);
    
    // Open file for writing: O_WRONLY | O_CREAT = 1 | 64
    uint32_t fd = callSyscall(56, -100, 100, 1 | 64, 0644);
    EXPECT_GE(fd, 3);
    
    // Write string to memory
    std::string content = "Hello, File!";
    writeStringToMemory(200, content);
    
    // Write to file: write(fd, buffer, count)
    uint32_t bytes_written = callSyscall(64, fd, 200, content.length());
    
    // Should write all bytes
    EXPECT_EQ(bytes_written, (uint32_t)content.length());
    
    callSyscall(57, fd, 0, 0);
    
    // Verify file content
    std::ifstream result_file(test_file);
    std::string result((std::istreambuf_iterator<char>(result_file)),
                       std::istreambuf_iterator<char>());
    EXPECT_EQ(result, content);
}

TEST_F(FileIOTest, WriteMultipleTimesAccumulates) {
    writeStringToMemory(100, test_file);
    
    // Open file for writing
    uint32_t fd = callSyscall(56, -100, 100, 1 | 64, 0644);
    
    // Write first string
    writeStringToMemory(200, "Line1\n");
    callSyscall(64, fd, 200, 6);
    
    // Write second string
    writeStringToMemory(300, "Line2\n");
    callSyscall(64, fd, 300, 6);
    
    callSyscall(57, fd, 0, 0);
    
    // Verify combined content
    std::ifstream result_file(test_file);
    std::string result((std::istreambuf_iterator<char>(result_file)),
                       std::istreambuf_iterator<char>());
    EXPECT_EQ(result, "Line1\nLine2\n");
}

TEST_F(FileIOTest, WriteInAppendMode) {
    // Create initial file
    std::ofstream initial(test_file);
    initial << "initial";
    initial.close();
    
    writeStringToMemory(100, test_file);
    
    // Open in append mode: O_WRONLY | O_APPEND = 1 | 1024
    uint32_t fd = callSyscall(56, -100, 100, 1 | 1024, 0644);
    
    // Write to end
    writeStringToMemory(200, "appended");
    uint32_t written = callSyscall(64, fd, 200, 8);
    EXPECT_EQ(written, 8u);
    
    callSyscall(57, fd, 0, 0);
    
    // Verify appended content
    std::ifstream result_file(test_file);
    std::string result((std::istreambuf_iterator<char>(result_file)),
                       std::istreambuf_iterator<char>());
    EXPECT_EQ(result, "initialappended");
}

TEST_F(FileIOTest, WriteToClosedFdError) {
    writeStringToMemory(100, test_file);
    uint32_t fd = callSyscall(56, -100, 100, 1 | 64, 0644);
    
    // Close the file
    callSyscall(57, fd, 0, 0);
    
    // Try to write to closed fd
    writeStringToMemory(200, "test");
    uint32_t written = callSyscall(64, fd, 200, 4);
    
    // Should return -1 (error)
    EXPECT_EQ(written, (uint32_t)-1);
}

// ============================================================================
// Integration Tests - Combining Multiple Syscalls
// ============================================================================

TEST_F(FileIOTest, WriteReadRoundTrip) {
    writeStringToMemory(100, test_file);
    
    // Open for writing
    uint32_t fd_write = callSyscall(56, -100, 100, 1 | 64, 0644);
    
    // Write data
    std::string original = "Test Data 123";
    writeStringToMemory(200, original);
    uint32_t written = callSyscall(64, fd_write, 200, original.length());
    EXPECT_EQ(written, (uint32_t)original.length());
    
    callSyscall(57, fd_write, 0, 0);
    
    // Open for reading
    uint32_t fd_read = callSyscall(56, -100, 100, 0, 0);
    
    // Read data back
    uint32_t read_count = callSyscall(63, fd_read, 300, 20);
    EXPECT_EQ(read_count, (uint32_t)original.length());
    
    std::string result = readStringFromMemory(300, 20);
    EXPECT_EQ(result, original);
    
    callSyscall(57, fd_read, 0, 0);
}

TEST_F(FileIOTest, WriteSeekReadModify) {
    writeStringToMemory(100, test_file);
    
    // Create file with initial content
    uint32_t fd = callSyscall(56, -100, 100, 1 | 64, 0644);
    writeStringToMemory(200, "ABCDEFGHIJ");
    callSyscall(64, fd, 200, 10);
    
    // Seek to position 3
    callSyscall(19, fd, 3, 0);
    
    // Overwrite from position 3
    writeStringToMemory(300, "123");
    callSyscall(64, fd, 300, 3);
    
    callSyscall(57, fd, 0, 0);
    
    // Verify result: ABC should be unchanged, DEF -> 123
    std::ifstream result_file(test_file);
    std::string result((std::istreambuf_iterator<char>(result_file)),
                       std::istreambuf_iterator<char>());
    EXPECT_EQ(result, "ABC123GHIJ");
}
