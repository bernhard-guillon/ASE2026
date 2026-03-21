// Syscall declarations
extern void exit(int status);
extern int write(int fd, const void *buf, unsigned long count);

// Simple recursive sum
int recursive_sum(int n) {
    if (n <= 0) {
        return 0;
    }
    return n + recursive_sum(n - 1);
}

// Simple recursive count down (just side effects)
void count_down(int n) {
    if (n <= 0) {
        return;
    }
    const char *msg = "x";
    write(1, msg, 1);
    count_down(n - 1);
}

// Fibonacci without optimizations
int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    write(1, "Testing recursive functions:\n", 29);
    
    // Test simple sum
    int sum = recursive_sum(5);  // 5+4+3+2+1 = 15
    write(1, "recursive_sum(5) completed\n", 27);
    
    // Test countdown
    write(1, "count_down(8): ", 14);
    count_down(8);
    write(1, "\n", 1);
    
    // Test fibonacci
    write(1, "fib(10) computed\n", 17);
    fib(10);
    
    write(1, "fib(12) computed\n", 17);
    fib(12);
    
    write(1, "All recursive tests completed!\n", 31);
    
    return 0;
}
