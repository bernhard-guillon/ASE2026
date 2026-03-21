// Syscall declarations
extern int write(int fd, const void *buf, unsigned long count);
extern int open(int dirfd, const char *pathname, int flags, unsigned int mode);
extern int read(int fd, void *buf, unsigned long count);
extern int close(int fd);
extern long lseek(int fd, long offset, int whence);

// Test lseek and write to file
int main() {
    // Create a test file
    int fd = open(0, "test_lseek_file.txt", 0x201, 0644);  // O_WRONLY | O_CREAT
    if (fd < 0) {
        write(2, "Failed to create file\n", 22);
        return 1;
    }
    
    // Write first part
    const char *msg1 = "Hello ";
    write(fd, msg1, 6);
    
    // Write second part
    const char *msg2 = "World!";
    write(fd, msg2, 6);
    
    // Seek back to position 6
    long pos = lseek(fd, 6, 0);  // SEEK_SET
    if (pos != 6) {
        write(2, "lseek failed\n", 13);
        return 1;
    }
    
    // Overwrite with different text
    const char *msg3 = "RISC-V";
    write(fd, msg3, 6);
    
    // Close the file
    close(fd);
    
    // Reopen for reading
    fd = open(0, "test_lseek_file.txt", 0x0, 0);  // O_RDONLY
    if (fd < 0) {
        write(2, "Failed to open file for reading\n", 32);
        return 1;
    }
    
    // Read and print the file
    char buffer[256];
    int bytes = read(fd, buffer, 256);
    
    close(fd);
    
    write(1, "File contents: ", 15);
    write(1, buffer, bytes);
    write(1, "\n", 1);
    
    return 0;
}
