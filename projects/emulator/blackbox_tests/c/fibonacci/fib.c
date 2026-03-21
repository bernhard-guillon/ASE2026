// Test memory access and loops
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    const char *msg = "Fibonacci: ";
    write(1, msg, 11);
    
    // Calculate fibonacci number using array
    int fib[10];
    fib[0] = 0;
    fib[1] = 1;
    
    int i;
    for (i = 2; i < 10; i++) {
        fib[i] = fib[i-1] + fib[i-2];
    }
    
    // Write first 5 fibonacci numbers as ASCII
    for (i = 0; i < 5; i++) {
        char digit = '0' + fib[i];
        write(1, &digit, 1);
        if (i < 4) {
            const char *comma = ",";
            write(1, comma, 1);
        }
    }
    
    const char *newline = "\n";
    write(1, newline, 1);
    
    return 0;
}
