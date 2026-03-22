/*
 * Floating-Point Extension (F) Test - C Version
 * Compiles with RISC-V GCC to test standard toolchain compatibility
 */

#include <stdio.h>

// Simple test functions
float test_add(float a, float b) {
    return a + b;
}

float test_multiply(float a, float b) {
    return a * b;
}

float test_relu(float x) {
    return (x > 0.0f) ? x : 0.0f;
}

float test_matrix_neuron(float w1, float x1, float w2, float x2, float bias) {
    // Single neuron: y = w1*x1 + w2*x2 + bias
    return w1 * x1 + w2 * x2 + bias;
}

int main() {
    float result;
    int pass_count = 0;
    int total_tests = 0;
    
    // Test 1: Addition
    total_tests++;
    result = test_add(2.5f, 3.5f);
    if (result == 6.0f) {
        printf("PASS: Addition (2.5 + 3.5 = %.1f)\n", result);
        pass_count++;
    } else {
        printf("FAIL: Addition expected 6.0, got %.6f\n", result);
    }
    
    // Test 2: Multiplication
    total_tests++;
    result = test_multiply(2.0f, 3.5f);
    if (result == 7.0f) {
        printf("PASS: Multiplication (2.0 * 3.5 = %.1f)\n", result);
        pass_count++;
    } else {
        printf("FAIL: Multiplication expected 7.0, got %.6f\n", result);
    }
    
    // Test 3: ReLU (negative input)
    total_tests++;
    result = test_relu(-5.5f);
    if (result == 0.0f) {
        printf("PASS: ReLU(-5.5) = %.1f\n", result);
        pass_count++;
    } else {
        printf("FAIL: ReLU expected 0.0, got %.6f\n", result);
    }
    
    // Test 4: ReLU (positive input)
    total_tests++;
    result = test_relu(7.25f);
    if (result == 7.25f) {
        printf("PASS: ReLU(7.25) = %.2f\n", result);
        pass_count++;
    } else {
        printf("FAIL: ReLU expected 7.25, got %.6f\n", result);
    }
    
    // Test 5: Matrix neuron (simulates neural network layer)
    total_tests++;
    result = test_matrix_neuron(0.5f, 1.0f, 1.5f, 2.0f, 2.5f);
    // Expected: 0.5*1.0 + 1.5*2.0 + 2.5 = 0.5 + 3.0 + 2.5 = 6.0
    if (result == 6.0f) {
        printf("PASS: Matrix neuron = %.1f\n", result);
        pass_count++;
    } else {
        printf("FAIL: Matrix neuron expected 6.0, got %.6f\n", result);
    }
    
    // Test 6: Division
    total_tests++;
    result = 10.0f / 2.0f;
    if (result == 5.0f) {
        printf("PASS: Division (10.0 / 2.0 = %.1f)\n", result);
        pass_count++;
    } else {
        printf("FAIL: Division expected 5.0, got %.6f\n", result);
    }
    
    // Test 7: Subtraction
    total_tests++;
    result = 10.0f - 3.5f;
    if (result == 6.5f) {
        printf("PASS: Subtraction (10.0 - 3.5 = %.1f)\n", result);
        pass_count++;
    } else {
        printf("FAIL: Subtraction expected 6.5, got %.6f\n", result);
    }
    
    // Test 8: Multiple operations
    total_tests++;
    float a = 2.0f, b = 3.0f, c = 4.0f;
    result = (a + b) * c;  // (2.0 + 3.0) * 4.0 = 20.0
    if (result == 20.0f) {
        printf("PASS: Complex expression ((2.0 + 3.0) * 4.0 = %.1f)\n", result);
        pass_count++;
    } else {
        printf("FAIL: Complex expression expected 20.0, got %.6f\n", result);
    }
    
    printf("\n");
    printf("========================================\n");
    printf("Test Results: %d/%d passed\n", pass_count, total_tests);
    printf("========================================\n");
    
    // Return 0 if all passed, 1 otherwise
    return (pass_count == total_tests) ? 0 : 1;
}
