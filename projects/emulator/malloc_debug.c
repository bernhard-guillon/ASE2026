// Debug program to test mmap directly
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
void* mmap(void *addr, unsigned long len, int prot, int flags, int fd, long pgoffset);

int main() {
    const char *msg = "Testing mmap: ";
    write(1, msg, 14);
    
    // Try to allocate 1024 bytes with MAP_ANONYMOUS
    void* ptr = mmap(0, 1024, 0, 0x20, -1, 0);
    
    // Check if mmap succeeded
    if ((unsigned long)ptr == (unsigned long)-1) {
        const char *err = "mmap failed\n";
        write(1, err, 12);
        return 1;
    }
    
    const char *ok = "ok\n";
    write(1, ok, 3);
    
    return 0;
}
