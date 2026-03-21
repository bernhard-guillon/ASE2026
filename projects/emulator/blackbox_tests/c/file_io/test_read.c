// Test reading from a file
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
int open(const char *pathname, int flags);
int read(int fd, void *buf, unsigned long count);
int close(int fd);

int main() {
    // Create a file first
    int fd_write = open("test.txt", 1 | 0x40);  // O_WRONLY | O_CREAT
    if (fd_write >= 0) {
        close(fd_write);
        write(1, "W", 1);
    }
    
    // Now try to read it
    int fd_read = open("test.txt", 0);  // O_RDONLY
    if (fd_read >= 0) {
        write(1, "R", 1);
        
        char buf[32];
        int n = read(fd_read, buf, 10);
        close(fd_read);
        
        if (n >= 0) {
            write(1, "D", 1);  // read succeeded
        } else {
            write(1, "E", 1);  // read failed
        }
    } else {
        write(1, "X", 1);  // open failed
    }
    
    write(1, "\n", 1);
    return 0;
}
