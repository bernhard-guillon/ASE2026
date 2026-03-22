#include <stdio.h>

int main(void) {
    float a = 2.0f;
    float b = 3.5f;
    float result = a * b;
    
    union { float f; unsigned int u; } actual, expected;
    actual.f = result;
    expected.f = 7.0f;
    
    printf("2.0 * 3.5 = %f\n", result);
    printf("actual bits:   0x%08x\n", actual.u);
    printf("expected bits: 0x%08x\n", expected.u);
    printf("match: %s\n", actual.u == expected.u ? "yes" : "no");
    
    return 0;
}
