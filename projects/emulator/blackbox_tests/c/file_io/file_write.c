// Test writing to a file
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
int open(int dirfd, const char *pathname, int flags, unsigned int mode);
int close(int fd);

int main() {
    const char *msg = "Creating file: ";
    write(1, msg, 15);
    
    // Try to create output.txt (O_WRONLY=1, O_CREAT=0x40)
    int flags = 1 | 0x40;  // O_WRONLY | O_CREAT
    int fd = open(0, "output.txt", flags, 0644);
    
    if (fd < 0) {
        const char *err = "open failed\n";
        write(1, err, 12);
        return 1;
    }
    
    const char *ok = "ok\n";
    write(1, ok, 3);
    
    // Write to file using write syscall
    const char *content = "Hello from file_write!\n";
    write(fd, content, 23);
    
    close(fd);
    
    const char *done = "File created\n";
    write(1, done, 13);
    
    return 0;
}
