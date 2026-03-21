// Syscall declarations
extern void exit(int status);
extern int write(int fd, const void *buf, unsigned long count);

// Mutual recursion test
int is_even(int n);
int is_odd(int n);

int is_even(int n) {
    if (n == 0) {
        return 1;  // true
    }
    return is_odd(n - 1);
}

int is_odd(int n) {
    if (n == 0) {
        return 0;  // false
    }
    return is_even(n - 1);
}

// Deep recursion stack test
void deep_call(int depth) {
    if (depth <= 0) {
        return;
    }
    deep_call(depth - 1);
}

// Indirect recursion: a -> b -> a
void func_a(int n);
void func_b(int n);

void func_a(int n) {
    if (n <= 0) {
        return;
    }
    const char *msg = "A";
    write(1, msg, 1);
    func_b(n - 1);
}

void func_b(int n) {
    if (n <= 0) {
        return;
    }
    const char *msg = "B";
    write(1, msg, 1);
    func_a(n - 1);
}

// Local variables in recursion
int sum_with_locals(int n) {
    int local1 = n;
    int local2 = n * 2;  // This uses multiplication, may need libgcc
    
    if (n <= 0) {
        return 0;
    }
    
    // Recursion happens after declaring locals
    return local1 + sum_with_locals(n - 1);
}

int main() {
    write(1, "Testing advanced recursion:\n", 28);
    
    // Test mutual recursion
    write(1, "is_even(8) = ", 13);
    if (is_even(8)) {
        write(1, "true\n", 5);
    } else {
        write(1, "false\n", 6);
    }
    
    write(1, "is_odd(8) = ", 12);
    if (is_odd(8)) {
        write(1, "true\n", 5);
    } else {
        write(1, "false\n", 6);
    }
    
    // Test deep recursion
    write(1, "deep_call(50) completed\n", 24);
    deep_call(50);
    
    // Test indirect recursion
    write(1, "Indirect recursion (10): ", 24);
    func_a(10);
    write(1, "\n", 1);
    
    // Test recursion with local variables
    write(1, "sum_with_locals(5) computed\n", 28);
    int result = sum_with_locals(5);
    
    write(1, "All advanced recursion tests completed!\n", 39);
    
    return 0;
}
