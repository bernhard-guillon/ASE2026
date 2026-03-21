// Minimal hello.c that works with bare-metal RISC-V toolchain
// Demonstrates direct syscalls

int write(int fd, const void *buf, unsigned long count);
int exit(int status);

int main() {
    const char *message = "Hello from C!\n";
    write(1, message, 14);
    return 0;
}

// We need exit to be called automatically by the C runtime
// This is a simplified version without libc
int _exit(int status) {
    exit(status);
    return 0;
}
