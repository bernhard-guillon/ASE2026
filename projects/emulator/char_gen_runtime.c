// Basic type definitions (no stdint.h dependency)
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;

#include "model.h"

#define MODEL_MAGIC 0x4E52414E

#define CODE_BASE 0x00001000u
#define GENERATOR_BASE 0x00030000u
#define RECOGNIZER_BASE 0x00110000u
#define BUFFER_BASE 0x00150000u
#define FRAMEBUFFER_BASE 0x00020000u

#define INPUT_BUF (BUFFER_BASE + 0x0000u)
#define ACTIVATION_A (BUFFER_BASE + 0x1000u)
#define ACTIVATION_B (BUFFER_BASE + 0x2000u)
#define OUTPUT_BUF (BUFFER_BASE + 0x3000u)

static inline uint32_t read_a0(void) {
    uint32_t value;
    __asm__ volatile ("mv %0, a0" : "=r"(value));
    return value;
}

static inline float sigmoid_pwl(float x) {
    if (x <= -4.0f) return 0.0f;
    if (x >= 4.0f) return 1.0f;
    return 0.5f + x * 0.125f;
}

static inline void map_input_generator(void) {
    volatile float *input = (volatile float *)INPUT_BUF;
    uint32_t code = read_a0();

    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) {
        input[i] = 0.0f;
    }

    if (code < MODEL_INPUT_SIZE) {
        input[code] = 1.0f;
    }
}

static inline void map_output_generator(void) {
    volatile float *output = (volatile float *)OUTPUT_BUF;
    volatile uint8_t *fb = (volatile uint8_t *)FRAMEBUFFER_BASE;

    for (uint32_t i = 0; i < MODEL_OUTPUT_SIZE; i++) {
        float v = output[i];
        if (v < 0.0f) v = 0.0f;
        if (v > 1.0f) v = 1.0f;
        v = v * 255.0f;
        uint32_t pixel = (uint32_t)v;
        if (pixel > 255u) pixel = 255u;
        fb[i] = (uint8_t)pixel;
    }
}

static inline void run_forward_pass(void) {
    const uint8_t *model_bytes = (const uint8_t *)model_data;
    const uint32_t *model_u32 = (const uint32_t *)model_data;

    if (model_u32[0] != MODEL_MAGIC) {
        return;
    }

    uint32_t num_layers = model_u32[3];
    uint32_t total_weights = model_u32[4];

    uint32_t layer_table_offset = MODEL_HEADER_SIZE;
    uint32_t weights_base = MODEL_HEADER_SIZE + num_layers * MODEL_LAYER_ENTRY_SIZE;
    uint32_t biases_base = weights_base + total_weights * 4u;

    volatile float *input_buf = (volatile float *)INPUT_BUF;
    volatile float *act_a = (volatile float *)ACTIVATION_A;
    volatile float *act_b = (volatile float *)ACTIVATION_B;
    volatile float *output_buf = (volatile float *)OUTPUT_BUF;

    for (uint32_t layer_idx = 0; layer_idx < num_layers; layer_idx++) {
        const uint32_t *layer = (const uint32_t *)(model_bytes + layer_table_offset + layer_idx * MODEL_LAYER_ENTRY_SIZE);
        uint32_t input_size = layer[0];
        uint32_t output_size = layer[1];
        uint32_t activation = layer[2];
        uint32_t weight_offset = layer[3];
        uint32_t bias_offset = layer[4];

        const float *weights = (const float *)(model_bytes + weights_base + weight_offset);
        const float *biases = (const float *)(model_bytes + biases_base + bias_offset);

        volatile float *input_ptr;
        volatile float *output_ptr;

        if (layer_idx == 0) {
            input_ptr = input_buf;
            output_ptr = act_a;
        } else if (layer_idx & 1u) {
            input_ptr = act_a;
            output_ptr = act_b;
        } else {
            input_ptr = act_b;
            output_ptr = act_a;
        }

        if (layer_idx == num_layers - 1) {
            output_ptr = output_buf;
        }

        for (uint32_t j = 0; j < output_size; j++) {
            float acc = biases[j];
            const float *wptr = weights + j;
            for (uint32_t i = 0; i < input_size; i++) {
                acc += input_ptr[i] * (*wptr);
                wptr += output_size;
            }

            if (activation == 1u) {
                if (acc < 0.0f) acc = 0.0f;
            } else if (activation == 2u) {
                acc = sigmoid_pwl(acc);
            }

            output_ptr[j] = acc;
        }
    }
}

void inference_loop(void);

__attribute__((naked)) void _start(void) {
    __asm__ volatile (
        "lui sp, 0x20\n"
        "jal ra, inference_loop\n"
    );
}

void inference_loop(void) {
    for (;;) {
        map_input_generator();
        run_forward_pass();
        map_output_generator();
    }
}
