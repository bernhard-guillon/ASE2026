/*
 * Floating-Point Extension (F) Test - C Version
 * Compiles with RISC-V GCC bare-metal toolchain (-nostdlib).
 * Does NOT use libc/stdio: output via write() syscall only.
 */

/* Bare-metal syscall declarations (provided by syscalls.s) */
extern int write(int fd, const void *buf, unsigned long count);

static void write_str(const char *s) {
    unsigned long len = 0;
    while (s[len]) len++;
    write(1, s, len);
}

/* Simple test functions */
static float fp_add(float a, float b) { return a + b; }
static float fp_mul(float a, float b) { return a * b; }
static float fp_sub(float a, float b) { return a - b; }
static float fp_relu(float x) { return (x > 0.0f) ? x : 0.0f; }

/* Single neuron: y = w1*x1 + w2*x2 + bias */
static float fp_neuron(float w1, float x1, float w2, float x2, float bias) {
    return w1 * x1 + w2 * x2 + bias;
}

int main(void) {
    int pass_count = 0;
    int total_tests = 0;
    float result;

    /* Test 1: Addition 2.5 + 3.5 = 6.0 */
    total_tests++;
    result = fp_add(2.5f, 3.5f);
    if (result == 6.0f) { write_str("PASS: Addition\n");       pass_count++; }
    else                 { write_str("FAIL: Addition\n"); }

    /* Test 2: Multiplication 2.0 * 3.5 = 7.0 */
    total_tests++;
    result = fp_mul(2.0f, 3.5f);
    if (result == 7.0f) { write_str("PASS: Multiplication\n"); pass_count++; }
    else                { write_str("FAIL: Multiplication\n"); }

    /* Test 3: Subtraction 10.0 - 3.5 = 6.5 */
    total_tests++;
    result = fp_sub(10.0f, 3.5f);
    if (result == 6.5f) { write_str("PASS: Subtraction\n");    pass_count++; }
    else                { write_str("FAIL: Subtraction\n"); }

    /* Test 4: ReLU of negative input -> 0.0 */
    total_tests++;
    result = fp_relu(-5.5f);
    if (result == 0.0f) { write_str("PASS: ReLU negative\n");  pass_count++; }
    else                { write_str("FAIL: ReLU negative\n"); }

    /* Test 5: ReLU of positive input passes through */
    total_tests++;
    result = fp_relu(7.25f);
    if (result == 7.25f) { write_str("PASS: ReLU positive\n"); pass_count++; }
    else                 { write_str("FAIL: ReLU positive\n"); }

    /* Test 6: Single neuron  0.5*1.0 + 1.5*2.0 + 2.5 = 6.0 */
    total_tests++;
    result = fp_neuron(0.5f, 1.0f, 1.5f, 2.0f, 2.5f);
    if (result == 6.0f) { write_str("PASS: Neuron\n");         pass_count++; }
    else                { write_str("FAIL: Neuron\n"); }

    /* Test 7: Division 10.0 / 2.0 = 5.0 */
    total_tests++;
    result = 10.0f / 2.0f;
    if (result == 5.0f) { write_str("PASS: Division\n");       pass_count++; }
    else                { write_str("FAIL: Division\n"); }

    /* Test 8: Combined (2.0 + 3.0) * 4.0 = 20.0 */
    total_tests++;
    result = fp_add(2.0f, 3.0f) * 4.0f;
    if (result == 20.0f) { write_str("PASS: Combined\n");      pass_count++; }
    else                 { write_str("FAIL: Combined\n"); }

    /* Return 0 only if every test passed */
    return (pass_count == total_tests) ? 0 : 1;
}
