/*
 * Pure C Sigmoid Activation Function Tests
 * 
 * Tests Sigmoid(x) using piecewise linear approximation.
 * Avoids exponential (not available in Phase 1).
 * Uses standard C with hard-float ABI.
 * 
 * Piecewise Linear Approximation:
 *   x <= -2.0: sigmoid ≈ 0.0
 *   -2.0 < x <= 0.0: sigmoid ≈ 0.25 + 0.125*x
 *   0.0 < x <= 2.0: sigmoid ≈ 0.75 + 0.125*x
 *   x > 2.0: sigmoid ≈ 1.0
 * 
 * This provides good accuracy for typical network range [-3, 3]
 * with only addition and multiplication (no exp needed).
 * 
 * Compilation: riscv64-elf-gcc -march=rv32imf -mabi=ilp32f (auto-detected)
 */

extern int write(int fd, const void *buf, unsigned long count);

static void write_str(const char *s) {
    unsigned long len = 0;
    while (s[len]) len++;
    write(1, s, len);
}

/* Pure C Sigmoid implementation using piecewise linear approximation */
static float sigmoid(float x) {
    if (x <= -2.0f) {
        return 0.0f;
    } else if (x <= 0.0f) {
        return 0.25f + 0.125f * x;
    } else if (x <= 2.0f) {
        return 0.75f + 0.125f * x;
    } else {
        return 1.0f;
    }
}

int main(void) {
    write_str("C_SIGMOID_TEST\n");
    
    /* Test 1: Large negative (should be ~0.0) */
    float test1 = sigmoid(-3.0f);
    if (test1 == 0.0f) {
        write_str("PASS: sigmoid(-3.0) = 0.0\n");
    } else {
        write_str("FAIL: sigmoid(-3.0)\n");
    }
    
    /* Test 2: -2.0 boundary */
    float test2 = sigmoid(-2.0f);
    if (test2 == 0.0f) {
        write_str("PASS: sigmoid(-2.0) = 0.0\n");
    } else {
        write_str("FAIL: sigmoid(-2.0)\n");
    }
    
    /* Test 3: -1.0 in linear region */
    float test3 = sigmoid(-1.0f);
    float expected3 = 0.25f - 0.125f;  // 0.125
    if (test3 == expected3) {
        write_str("PASS: sigmoid(-1.0) = 0.125\n");
    } else {
        write_str("FAIL: sigmoid(-1.0)\n");
    }
    
    /* Test 4: Zero crossing */
    float test4 = sigmoid(0.0f);
    if (test4 == 0.5f) {
        write_str("PASS: sigmoid(0.0) = 0.5\n");
    } else {
        write_str("FAIL: sigmoid(0.0)\n");
    }
    
    /* Test 5: Positive linear region */
    float test5 = sigmoid(1.0f);
    float expected5 = 0.75f + 0.125f;  // 0.875
    if (test5 == expected5) {
        write_str("PASS: sigmoid(1.0) = 0.875\n");
    } else {
        write_str("FAIL: sigmoid(1.0)\n");
    }
    
    /* Test 6: 2.0 boundary */
    float test6 = sigmoid(2.0f);
    if (test6 == 1.0f) {
        write_str("PASS: sigmoid(2.0) = 1.0\n");
    } else {
        write_str("FAIL: sigmoid(2.0)\n");
    }
    
    /* Test 7: Large positive (should be ~1.0) */
    float test7 = sigmoid(3.0f);
    if (test7 == 1.0f) {
        write_str("PASS: sigmoid(3.0) = 1.0\n");
    } else {
        write_str("FAIL: sigmoid(3.0)\n");
    }
    
    /* Test 8: Symmetry property: sigmoid(x) + sigmoid(-x) ≈ 1.0 */
    float pos = sigmoid(0.5f);
    float neg = sigmoid(-0.5f);
    float sum = pos + neg;
    if (sum == 1.0f) {
        write_str("PASS: symmetry property\n");
    } else {
        write_str("FAIL: symmetry property\n");
    }
    
    write_str("END_C_SIGMOID_TEST\n");
    
    return 0;
}
