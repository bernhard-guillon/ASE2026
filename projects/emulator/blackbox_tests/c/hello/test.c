// Test C program demonstrating more complex operations
int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    const char *msg1 = "2 + 3 = ";
    write(1, msg1, 8);
    
    // Simple calculation
    int a = 2;
    int b = 3;
    int sum = a + b;
    
    // Write the result (as ASCII digit)
    char result_char = '0' + sum;
    write(1, &result_char, 1);
    
    const char *newline = "\n";
    write(1, newline, 1);
    
    return 0;
}
