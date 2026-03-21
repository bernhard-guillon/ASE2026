// Test reading from a file
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
int open(const char *pathname, int flags);
int read(int fd, void *buf, unsigned long count);
int close(int fd);

int main() {
    const char *msg = "Opening file: ";
    write(1, msg, 14);
    
    // Try to open test_data.txt
    int fd = open("test_data.txt", 0);  // O_RDONLY = 0
    
    if (fd < 0) {
        const char *err = "open failed\n";
        write(1, err, 12);
        return 1;
    }
    
    const char *ok = "ok\n";
    write(1, ok, 3);
    
    // Read file content
    const char *msg2 = "Reading content: ";
    write(1, msg2, 17);
    
    char buffer[256];
    int bytes_read = read(fd, buffer, 256);
    
    if (bytes_read < 0) {
        const char *err2 = "read failed\n";
        write(1, err2, 12);
        close(fd);
        return 1;
    }
    
    // Write what we read
    write(1, buffer, bytes_read);
    
    if (bytes_read > 0 && buffer[bytes_read - 1] != '\n') {
        write(1, "\n", 1);
    }
    
    // Close file
    close(fd);
    
    const char *done = "Success\n";
    write(1, done, 8);
    
    return 0;
}
