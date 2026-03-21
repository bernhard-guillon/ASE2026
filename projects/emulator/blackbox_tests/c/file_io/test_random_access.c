// Syscall declarations
extern int write(int fd, const void *buf, unsigned long count);
extern int open(int dirfd, const char *pathname, int flags, unsigned int mode);
extern int read(int fd, void *buf, unsigned long count);
extern int close(int fd);
extern long lseek(int fd, long offset, int whence);

// Test random access: write at different positions
int main() {
    // Create a test file with specific content
    int fd = open(0, "test_random.txt", 0x201, 0644);  // O_WRONLY | O_CREAT
    if (fd < 0) {
        write(2, "Failed to create file\n", 22);
        return 1;
    }
    
    // Write "0123456789" (10 bytes)
    const char *initial = "0123456789";
    write(fd, initial, 10);
    
    // Seek to position 2 and write "XX"
    lseek(fd, 2, 0);
    const char *part1 = "XX";
    write(fd, part1, 2);
    
    // Seek to position 7 and write "YY"
    lseek(fd, 7, 0);
    const char *part2 = "YY";
    write(fd, part2, 2);
    
    // Seek to end and append "!"
    lseek(fd, 0, 2);  // SEEK_END
    const char *end = "!";
    write(fd, end, 1);
    
    close(fd);
    
    // Reopen and read the file
    fd = open(0, "test_random.txt", 0x0, 0);  // O_RDONLY
    if (fd < 0) {
        write(2, "Failed to open file for reading\n", 32);
        return 1;
    }
    
    char buffer[256];
    int bytes = read(fd, buffer, 256);
    close(fd);
    
    write(1, "Result: ", 8);
    write(1, buffer, bytes);
    write(1, " (expected: 01XX456YY9!)\n", 25);
    
    return 0;
}
