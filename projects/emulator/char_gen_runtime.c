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

// Character code preserved in callee-saved register s1
// Set once by _start from the initial a0, then never touched by C code
register uint32_t char_code asm("s1");

// Descriptor for nmatvec custom instruction (32 bytes)
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

// nmatvecx.f32 a0, t0  ->  .word 0x0000557B
// opcode=0x7B, rd=a0(10), rs1=t0(5), opid=0
static inline uint32_t neural_matvec(const neural_desc_t *desc) {
    register uint32_t dp asm("t0") = (uint32_t)desc;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x557B\n" : "=r"(st) : "r"(dp) : "memory");
    return st;
}

// nvrelux.f32 a0, t1, t2, t3  ->  .word 0x0F0E657B
// opcode=0x7B, rd=a0(10), rs1=t1(6), rs2=t2(7), rs3=t3(28), opid=1
static inline uint32_t neural_relu(float *dst, const float *src, uint32_t len) {
    register uint32_t d asm("t1") = (uint32_t)dst;
    register uint32_t s asm("t2") = (uint32_t)src;
    register uint32_t n asm("t3") = len;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x0F0E657B\n" : "=r"(st) : "r"(d), "r"(s), "r"(n) : "memory");
    return st;
}

// nvsigpwlx.f32 a0, t1, t2, t3  ->  .word 0x170E657B
// opcode=0x7B, rd=a0(10), rs1=t1(6), rs2=t2(7), rs3=t3(28), opid=2
static inline uint32_t neural_sigmoid(float *dst, const float *src, uint32_t len) {
    register uint32_t d asm("t1") = (uint32_t)dst;
    register uint32_t s asm("t2") = (uint32_t)src;
    register uint32_t n asm("t3") = len;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x170E657B\n" : "=r"(st) : "r"(d), "r"(s), "r"(n) : "memory");
    return st;
}

// nvclampu8x.f32 a0, t1, t2, t3  ->  .word 0x1F0E657B
// opcode=0x7B, rd=a0(10), rs1=t1(6), rs2=t2(7), rs3=t3(28), opid=3
static inline uint32_t neural_clamp_u8(uint8_t *dst, const float *src, uint32_t len) {
    register uint32_t d asm("t1") = (uint32_t)dst;
    register uint32_t s asm("t2") = (uint32_t)src;
    register uint32_t n asm("t3") = len;
    register uint32_t st asm("a0");
    __asm__ volatile(".word 0x1F0E657B\n" : "=r"(st) : "r"(d), "r"(s), "r"(n) : "memory");
    return st;
}

static inline void map_input_generator(void) {
    volatile float *input = (volatile float *)INPUT_BUF;

    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) {
        input[i] = 0.0f;
    }

    if (char_code < MODEL_INPUT_SIZE) {
        input[char_code] = 1.0f;
    }
}

static inline void map_output_generator(void) {
    neural_clamp_u8((uint8_t *)FRAMEBUFFER_BASE, (const float *)OUTPUT_BUF, MODEL_OUTPUT_SIZE);
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
    for (;;) {
        map_input_generator();
        run_forward_pass();
        map_output_generator();
    }
}
