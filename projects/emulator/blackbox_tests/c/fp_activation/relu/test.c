/*
 * Pure C ReLU Activation Function Tests
 * 
 * Tests ReLU(x) = max(x, 0.0) using standard C with hard-float ABI.
 * This validates that GCC can compile FP C code correctly.
 * 
 * Compilation: riscv64-elf-gcc -march=rv32imf -mabi=ilp32f (auto-detected)
 */

extern int write(int fd, const void *buf, unsigned long count);

static void write_str(const char *s) {
    unsigned long len = 0;
    while (s[len]) len++;
    write(1, s, len);
}

/* Pure C ReLU implementation */
static float relu(float x) {
    return (x > 0.0f) ? x : 0.0f;
}

int main(void) {
    write_str("C_RELU_TEST\n");
    
    /* Test 1: Negative input */
    float test1 = relu(-5.5f);
    if (test1 == 0.0f) {
        write_str("PASS: relu(-5.5) = 0.0\n");
    } else {
        write_str("FAIL: relu(-5.5)\n");
    }
    
    /* Test 2: Positive input */
    float test2 = relu(2.5f);
    if (test2 == 2.5f) {
        write_str("PASS: relu(2.5) = 2.5\n");
    } else {
        write_str("FAIL: relu(2.5)\n");
    }
    
    /* Test 3: Zero input */
    float test3 = relu(0.0f);
    if (test3 == 0.0f) {
        write_str("PASS: relu(0.0) = 0.0\n");
    } else {
        write_str("FAIL: relu(0.0)\n");
    }
    
    /* Test 4: Small negative */
    float test4 = relu(-0.001f);
    if (test4 == 0.0f) {
        write_str("PASS: relu(-0.001) = 0.0\n");
    } else {
        write_str("FAIL: relu(-0.001)\n");
    }
    
    /* Test 5: Small positive */
    float test5 = relu(0.001f);
    if (test5 == 0.001f) {
        write_str("PASS: relu(0.001) = 0.001\n");
    } else {
        write_str("FAIL: relu(0.001)\n");
    }
    
    /* Test 6: Large positive */
    float test6 = relu(100.0f);
    if (test6 == 100.0f) {
        write_str("PASS: relu(100.0) = 100.0\n");
    } else {
        write_str("FAIL: relu(100.0)\n");
    }
    
    /* Test 7: Large negative */
    float test7 = relu(-100.0f);
    if (test7 == 0.0f) {
        write_str("PASS: relu(-100.0) = 0.0\n");
    } else {
        write_str("FAIL: relu(-100.0)\n");
    }
    
    /* Test 8: Chain of ReLUs */
    float chain = relu(relu(-1.0f) - 2.0f);  // relu(0.0 - 2.0) = relu(-2.0) = 0.0
    if (chain == 0.0f) {
        write_str("PASS: chained relu\n");
    } else {
        write_str("FAIL: chained relu\n");
    }
    
    write_str("END_C_RELU_TEST\n");
    
    return 0;
}
