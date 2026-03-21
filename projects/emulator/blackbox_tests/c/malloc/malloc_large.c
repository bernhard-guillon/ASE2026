// Test: Allocate, use, and free memory
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
extern void* malloc(unsigned long size);
extern int free(void *ptr);

int main() {
    const char *msg = "Large allocation test: ";
    write(1, msg, 23);
    
    // Allocate larger block (10KB)
    int *big_arr = (int*)malloc(10240);
    
    if (big_arr == 0) {
        const char *err = "failed\n";
        write(1, err, 7);
        return 1;
    }
    
    // Fill array
    int i;
    for (i = 0; i < 100; i++) {
        big_arr[i] = i;
    }
    
    // Verify data
    if (big_arr[50] == 50 && big_arr[99] == 99) {
        const char *ok = "ok\n";
        write(1, ok, 3);
    } else {
        const char *bad = "data corruption\n";
        write(1, bad, 16);
        return 1;
    }
    
    free(big_arr);
    return 0;
}
