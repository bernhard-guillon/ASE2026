// Test program that uses malloc from shared malloc.c
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

// Declare malloc and free from malloc.c
extern void* malloc(unsigned long size);
extern int free(void *ptr);

int main() {
    const char *msg1 = "Testing malloc: ";
    write(1, msg1, 16);
    
    // Allocate some memory
    int *arr = (int*)malloc(20 * sizeof(int));
    
    if (arr == 0) {
        const char *err = "failed\n";
        write(1, err, 7);
        return 1;
    }
    
    // Use the allocated memory
    arr[0] = 7;
    arr[1] = 9;
    arr[2] = arr[0] + arr[1];
    
    // Print success
    const char *ok = "success\n";
    write(1, ok, 8);
    
    return 0;
}
