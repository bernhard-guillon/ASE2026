// Test: Multiple allocations
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
extern void* malloc(unsigned long size);
extern int free(void *ptr);

int main() {
    const char *msg = "Multiple alloc test: ";
    write(1, msg, 20);
    
    // Allocate 3 different sizes
    int *a = (int*)malloc(128);
    char *b = (char*)malloc(256);
    int *c = (int*)malloc(512);
    
    if (a == 0 || b == 0 || c == 0) {
        const char *err = "alloc failed\n";
        write(1, err, 13);
        return 1;
    }
    
    // Use all three
    a[0] = 111;
    b[0] = 'X';
    c[0] = 222;
    
    // Verify
    if (a[0] == 111 && b[0] == 'X' && c[0] == 222) {
        const char *ok = "ok\n";
        write(1, ok, 3);
        
        // Free all
        free(a);
        free(b);
        free(c);
        
        return 0;
    } else {
        const char *bad = "verify failed\n";
        write(1, bad, 14);
        return 1;
    }
}
