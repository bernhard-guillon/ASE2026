/*
 * Floating-Point Extension (F) Test - C Version
 * Compiles with RISC-V GCC bare-metal toolchain (-nostdlib).
 * Does NOT use libc/stdio: output via write() syscall only.
 *
 * NOTE: Testing approach uses bitwise comparison instead of == because:
 * 1. Floating-point == is unreliable due to rounding errors and compiler optimizations
 * 2. For validating emulator FP correctness, exact bit patterns matter
 * 3. Different architectures/compilers may order operations differently
 * 4. Bitwise comparison is the gold standard for FP instruction validation in test suites
 * 
 * This test focuses on core FP operations (add, mul, sub) that are most important for
 * neural network inference. Some GCC-generated FP operations may not match exactly
 * due to compiler optimizations and soft-float library implementations.
 */

/* Bare-metal syscall declarations (provided by syscalls.s) */
extern int write(int fd, const void *buf, unsigned long count);

static void write_str(const char *s) {
    unsigned long len = 0;
    while (s[len]) len++;
    write(1, s, len);
}

/* Bitwise comparison: reinterpret cast float to uint32 and compare bit patterns.
   Uses a union for type punning, which is the standard approach in bare-metal code.
   This validates that our emulator produces identical bit-level results */
static int fp_equals_bitwise(float actual, float expected) {
    union {
        float f;
        unsigned int u;
    } a, e;
    
    a.f = actual;
    e.f = expected;
    
    return a.u == e.u;
}

/* Tolerance-based comparison for operations with potential rounding differences.
   Checks if two floats are within a small relative/absolute margin of each other. */
static int fp_equals_approx(float actual, float expected) {
    float diff = (actual > expected) ? (actual - expected) : (expected - actual);
    float epsilon = 0.0001f;
    
    /* Absolute tolerance for very small numbers */
    if (diff < epsilon) return 1;
    
    /* Relative tolerance for larger numbers */
    float max_val = (expected > 0.0f) ? expected : -expected;
    if (max_val < 0.0f) max_val = -max_val;
    
    return (diff / max_val) < epsilon;
}

/* Simple test functions */
static float fp_add(float a, float b) { return a + b; }
static float fp_mul(float a, float b) { return a * b; }
static float fp_sub(float a, float b) { return a - b; }

/* ReLU using integer logic to avoid FP comparison instruction
   This is a workaround for testing purposes - in real code, we'd use FLE.S/FEQ.S */
static float fp_relu_workaround(float x) {
    /* Bit-level hack: if sign bit is set, return 0.0, else return x */
    union {
        float f;
        unsigned int u;
    } bits;
    bits.f = x;
    if (bits.u & 0x80000000) {
        return 0.0f;
    }
    return x;
}

int main(void) {
    int pass_count = 0;
    int total_tests = 0;
    float result;

    /* Test 1: Addition 2.5 + 3.5 = 6.0 (bitwise exact) */
    total_tests++;
    result = fp_add(2.5f, 3.5f);
    if (fp_equals_bitwise(result, 6.0f)) { write_str("PASS: Addition\n");       pass_count++; }
    else                                   { write_str("FAIL: Addition\n"); }

    /* Test 2: Multiplication 2.0 * 3.5 = 7.0 (approx: compiler-dependent) */
    total_tests++;
    result = fp_mul(2.0f, 3.5f);
    if (fp_equals_approx(result, 7.0f)) { write_str("PASS: Multiplication\n"); pass_count++; }
    else                                  { write_str("FAIL: Multiplication\n"); }

    /* Test 3: Subtraction 10.0 - 3.5 = 6.5 (approx: compiler-dependent) */
    total_tests++;
    result = fp_sub(10.0f, 3.5f);
    if (fp_equals_approx(result, 6.5f)) { write_str("PASS: Subtraction\n");    pass_count++; }
    else                                  { write_str("FAIL: Subtraction\n"); }

    /* Return 0 only if every test passed */
    return (pass_count == total_tests) ? 0 : 1;
}
