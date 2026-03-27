#ifndef NEURAL_OPS_H
#define NEURAL_OPS_H

#include <cstdint>
#include <vector>
#include <cmath>
#include <cstring>

/**
 * Neural Operations (Phase B Foundation)
 * 
 * Implements scalar versions of planned neural instructions:
 * - NMATVEC.F32: matrix-vector multiply with bias
 * - NVRELU.F32: elementwise ReLU
 * - NVSIGPWL.F32: elementwise piecewise sigmoid
 * - NVCLAMPU8.F32: float->u8 clamped conversion
 */

class NeuralOps {
public:
    // Error codes (non-zero = error, zero = success)
    static constexpr uint32_t ERR_OK = 0;
    static constexpr uint32_t ERR_INVALID_PTR = 1;
    static constexpr uint32_t ERR_INVALID_LEN = 2;
    static constexpr uint32_t ERR_UNALIGNED = 3;
    static constexpr uint32_t ERR_OVERLAP = 4;

    /**
     * NMATVEC.F32: Dense layer compute
     * 
     * Descriptor at memory address `desc_addr`:
     *   +0x00: input_ptr       (u32)
     *   +0x04: weights_ptr     (u32)
     *   +0x08: bias_ptr        (u32)
     *   +0x0C: output_ptr      (u32)
     *   +0x10: input_len       (u32)
     *   +0x14: output_len      (u32)
     *   +0x18: flags           (u32, must be 0)
     *   +0x1C: reserved        (u32)
     * 
     * Computes for each output j:
     *   out[j] = bias[j] + sum(i=0..input_len-1) input[i] * weight[i*output_len+j]
     * 
     * Returns error code in rd_status (0 = success).
     */
    static uint32_t matvec_f32(
        const std::vector<uint8_t>& memory,
        uint32_t desc_addr
    );

    /**
     * NVRELU.F32: Elementwise ReLU
     * 
     * dst[i] = max(src[i], 0.0) for i in [0, len)
     * 
     * dst and src may alias (in-place allowed).
     * Returns error code in rd_status (0 = success).
     */
    static uint32_t vec_relu_f32(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr,
        uint32_t src_ptr,
        uint32_t len
    );

    /**
     * NVSIGPWL.F32: Piecewise sigmoid approximation
     * 
     * if x <= -4: y = 0
     * else if x >= 4: y = 1
     * else: y = 0.5 + x*0.125
     * 
     * dst and src may alias (in-place allowed).
     * Returns error code in rd_status (0 = success).
     */
    static uint32_t vec_sigmoid_pwl_f32(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr,
        uint32_t src_ptr,
        uint32_t len
    );

    /**
     * NVCLAMPU8.F32: Float to byte conversion
     * 
     * Clamps float to [0, 1], scales by 255, truncates to u8.
     * NaN -> 0, out of range clamped.
     * 
     * Returns error code in rd_status (0 = success).
     */
    static uint32_t vec_clamp_scale_u8_f32(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr_u8,
        uint32_t src_ptr_f32,
        uint32_t len
    );

    // Enhanced kernels for CUSTOM3 (0x7B). Semantics must match v1 methods.
    static uint32_t matvec_f32_v2(
        std::vector<uint8_t>& memory,
        uint32_t desc_addr
    );

    static uint32_t vec_relu_f32_v2(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr,
        uint32_t src_ptr,
        uint32_t len
    );

    static uint32_t vec_sigmoid_pwl_f32_v2(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr,
        uint32_t src_ptr,
        uint32_t len
    );

    static uint32_t vec_clamp_scale_u8_f32_v2(
        std::vector<uint8_t>& memory,
        uint32_t dst_ptr_u8,
        uint32_t src_ptr_f32,
        uint32_t len
    );

private:
    // Helper: read float32 from memory at aligned address
    static float read_f32(const std::vector<uint8_t>& mem, uint32_t addr);
    static void write_f32(std::vector<uint8_t>& mem, uint32_t addr, float val);
    
    // Helper: read u32 from memory at aligned address
    static uint32_t read_u32(const std::vector<uint8_t>& mem, uint32_t addr);
    
    // Helper: validate pointer alignment and bounds
    static bool is_aligned(uint32_t addr, uint32_t align);
    static bool is_valid_ptr(const std::vector<uint8_t>& mem, uint32_t addr, uint32_t size);
};

#endif // NEURAL_OPS_H
