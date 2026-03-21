// Minimal test to debug open
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
int open(const char *pathname, int flags);

int main() {
    write(1, "A", 1);
    
    int fd = open("test.txt", 0);
    
    write(1, "B", 1);
    
    if (fd >= 0) {
        write(1, "O", 1);  // open succeeded
    } else {
        write(1, "F", 1);  // open failed
    }
    
    write(1, "\n", 1);
    
    return 0;
}
