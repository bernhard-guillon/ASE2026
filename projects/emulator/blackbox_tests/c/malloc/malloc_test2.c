// Test program using malloc for dynamic allocation
int write(int fd, const void *buf, unsigned long count);
int exit(int status);
extern void* malloc(unsigned long size);
extern int free(void *ptr);

int main() {
    const char *msg1 = "Allocating 64 bytes: ";
    write(1, msg1, 21);
    
    // Allocate memory dynamically
    int *arr = (int*)malloc(64);
    
    if (arr == 0) {
        const char *err = "malloc failed\n";
        write(1, err, 14);
        return 1;
    }
    
    // Use the allocated memory
    arr[0] = 10;
    arr[1] = 20;
    arr[2] = 30;
    arr[3] = arr[0] + arr[1] + arr[2];  // 60
    
    // Print success message
    const char *success = "success\n";
    write(1, success, 8);
    
    // Free memory
    free(arr);
    
    // Allocate again
    const char *msg2 = "Second allocation: ";
    write(1, msg2, 19);
    
    char *buf = (char*)malloc(32);
    if (buf == 0) {
        const char *err2 = "second malloc failed\n";
        write(1, err2, 21);
        return 1;
    }
    
    buf[0] = 'O';
    buf[1] = 'K';
    buf[2] = '\n';
    write(1, buf, 3);
    
    free(buf);
    
    return 0;
}
