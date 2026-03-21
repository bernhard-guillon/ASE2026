/*
 * Test program for model loader.
 * Verifies that binary models can be loaded and inspected.
 */

#include "model_loader.h"
#include <stdio.h>

int main() {
    printf("Neural Network Model Loader Test\n");
    printf("=================================\n\n");

    // Test loading generator model
    printf("1. Loading character generator model...\n");
    Model *gen_model = model_load_from_file("character_generator.bin");
    if (gen_model) {
        model_print_info(gen_model);
        model_free(gen_model);
        printf("✓ Generator model loaded successfully\n\n");
    } else {
        printf("✗ Failed to load generator model\n\n");
    }

    // Test loading recognizer model
    printf("2. Loading character recognizer model...\n");
    Model *recog_model = model_load_from_file("character_recognition.bin");
    if (recog_model) {
        model_print_info(recog_model);
        model_free(recog_model);
        printf("✓ Recognizer model loaded successfully\n\n");
    } else {
        printf("✗ Failed to load recognizer model\n\n");
    }

    printf("All tests completed!\n");
    return 0;
}
