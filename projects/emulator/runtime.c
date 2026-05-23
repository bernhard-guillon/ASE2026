typedef unsigned int uint32_t;
typedef unsigned char uint8_t;

#include "model.h"

#define MODEL_MAGIC 0x4E52414E

#define BUFFER_BASE 0x00150000u
#define FRAMEBUFFER_BASE 0x00020000u

#define INPUT_BUF (BUFFER_BASE + 0x0000u)
#define ACTIVATION_A (BUFFER_BASE + 0x1000u)
#define ACTIVATION_B (BUFFER_BASE + 0x2000u)
#define OUTPUT_BUF (BUFFER_BASE + 0x3000u)
#define DONE_FLAG_ADDR (BUFFER_BASE + 0x4000u)

typedef struct {
    uint32_t input_ptr;
    uint32_t weights_ptr;
    uint32_t bias_ptr;
    uint32_t output_ptr;
    uint32_t input_len;
    uint32_t output_len;
    uint32_t flags;
    uint32_t reserved;
} __attribute__((packed)) neural_desc_t;

static inline uint32_t neural_matvec(const neural_desc_t *desc) {
    register uint32_t dp asm("t0") = (uint32_t)desc;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x557B\n" : "=r"(st) : "r"(dp) : "memory");
    return st;
}

static inline uint32_t neural_relu(float *dst, const float *src, uint32_t len) {
    register uint32_t d asm("t1") = (uint32_t)dst;
    register uint32_t s asm("t2") = (uint32_t)src;
    register uint32_t n asm("t3") = len;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x0F0E657B\n" : "=r"(st) : "r"(d), "r"(s), "r"(n) : "memory");
    return st;
}

static inline uint32_t neural_sigmoid(float *dst, const float *src, uint32_t len) {
    register uint32_t d asm("t1") = (uint32_t)dst;
    register uint32_t s asm("t2") = (uint32_t)src;
    register uint32_t n asm("t3") = len;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x170E657B\n" : "=r"(st) : "r"(d), "r"(s), "r"(n) : "memory");
    return st;
}

static inline void run_forward_pass(void) {
    const uint8_t *model_bytes = (const uint8_t *)model_data;
    const uint32_t *model_u32 = (const uint32_t *)model_data;

    if (model_u32[0] != MODEL_MAGIC) return;

    uint32_t num_layers = model_u32[3];
    uint32_t total_weights = model_u32[4];

    uint32_t layer_table_offset = MODEL_HEADER_SIZE;
    uint32_t weights_base = MODEL_HEADER_SIZE + num_layers * MODEL_LAYER_ENTRY_SIZE;
    uint32_t biases_base = weights_base + total_weights * 4u;

    for (uint32_t layer_idx = 0; layer_idx < num_layers; layer_idx++) {
        const uint32_t *layer = (const uint32_t *)(model_bytes + layer_table_offset + layer_idx * MODEL_LAYER_ENTRY_SIZE);
        uint32_t input_size = layer[0];
        uint32_t output_size = layer[1];
        uint32_t activation = layer[2];
        uint32_t weight_offset = layer[3];
        uint32_t bias_offset = layer[4];

        uint32_t weights_addr = (uint32_t)(model_bytes + weights_base + weight_offset);
        uint32_t biases_addr = (uint32_t)(model_bytes + biases_base + bias_offset);

        uint32_t input_addr, output_addr;

        if (layer_idx == 0) {
            input_addr = INPUT_BUF;
            output_addr = ACTIVATION_A;
        } else if (layer_idx & 1u) {
            input_addr = ACTIVATION_A;
            output_addr = ACTIVATION_B;
        } else {
            input_addr = ACTIVATION_B;
            output_addr = ACTIVATION_A;
        }

        if (layer_idx == num_layers - 1) {
            output_addr = OUTPUT_BUF;
        }

        neural_desc_t desc;
        desc.input_ptr = input_addr;
        desc.weights_ptr = weights_addr;
        desc.bias_ptr = biases_addr;
        desc.output_ptr = output_addr;
        desc.input_len = input_size;
        desc.output_len = output_size;
        desc.flags = 0;
        desc.reserved = 0;

        neural_matvec(&desc);

        if (activation == 0u) {
            neural_relu((float *)output_addr, (float *)output_addr, output_size);
        } else if (activation == 1u) {
            neural_sigmoid((float *)output_addr, (float *)output_addr, output_size);
        }
    }
}

void inference_loop(void);

__attribute__((naked)) void _start(void) {
    __asm__ volatile (
        "lui sp, 0x20\n"
        "mv s1, a0\n"
        "jal ra, inference_loop\n"
    );
}

void inference_loop(void) {
    volatile uint32_t *done_flag = (volatile uint32_t *)DONE_FLAG_ADDR;
    volatile float *input = (volatile float *)INPUT_BUF;
    volatile float *output = (volatile float *)OUTPUT_BUF;
    volatile uint8_t *fb = (volatile uint8_t *)FRAMEBUFFER_BASE;

    for (;;) {
        MODEL_MAP_INPUT(input);

        run_forward_pass();

        MODEL_MAP_OUTPUT(output, fb);

        if (MODEL_HAS_DONE_FLAG) {
            *done_flag = 1;
        }
    }
}
