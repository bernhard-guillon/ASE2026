#include "NeuralOps.h"

namespace {
bool checked_mul_u32(uint32_t a, uint32_t b, uint32_t* out) {
    const uint64_t prod = static_cast<uint64_t>(a) * static_cast<uint64_t>(b);
    if (prod > 0xFFFFFFFFull) {
        return false;
    }
    *out = static_cast<uint32_t>(prod);
    return true;
}

bool checked_mul4_u32(uint32_t elems, uint32_t* out) {
    if (elems > (0xFFFFFFFFu >> 2)) {
        return false;
    }
    *out = elems << 2;
    return true;
}

bool compute_matvec_sizes(
    uint32_t input_len,
    uint32_t output_len,
    uint32_t* input_size,
    uint32_t* weights_size,
    uint32_t* bias_size,
    uint32_t* output_size
) {
    uint32_t weight_elems = 0;
    if (!checked_mul_u32(input_len, output_len, &weight_elems)) {
        return false;
    }
    return checked_mul4_u32(input_len, input_size) &&
           checked_mul4_u32(weight_elems, weights_size) &&
           checked_mul4_u32(output_len, bias_size) &&
           checked_mul4_u32(output_len, output_size);
}
}  // namespace

// Helper: read float32 from memory
float NeuralOps::read_f32(const std::vector<uint8_t>& mem, uint32_t addr) {
    if (addr + 4 > mem.size()) return 0.0f;
    uint32_t bits = 0;
    std::memcpy(&bits, &mem[addr], 4);
    float val;
    std::memcpy(&val, &bits, 4);
    return val;
}

void NeuralOps::write_f32(std::vector<uint8_t>& mem, uint32_t addr, float val) {
    if (addr + 4 > mem.size()) return;
    uint32_t bits;
    std::memcpy(&bits, &val, 4);
    std::memcpy(&mem[addr], &bits, 4);
}

uint32_t NeuralOps::read_u32(const std::vector<uint8_t>& mem, uint32_t addr) {
    if (addr + 4 > mem.size()) return 0;
    uint32_t val = 0;
    std::memcpy(&val, &mem[addr], 4);
    return val;
}

bool NeuralOps::is_aligned(uint32_t addr, uint32_t align) {
    return (addr % align) == 0;
}

bool NeuralOps::is_valid_ptr(const std::vector<uint8_t>& mem, uint32_t addr, uint32_t size) {
    const size_t base = static_cast<size_t>(addr);
    const size_t bytes = static_cast<size_t>(size);
    if (base > mem.size()) return false;
    return bytes <= (mem.size() - base);
}

// NMATVEC.F32 implementation
uint32_t NeuralOps::matvec_f32(
    const std::vector<uint8_t>& memory,
    uint32_t desc_addr
) {
    // Read descriptor
    if (!is_valid_ptr(memory, desc_addr, 32)) {
        return ERR_INVALID_PTR;
    }
    
    uint32_t input_ptr = read_u32(memory, desc_addr + 0x00);
    uint32_t weights_ptr = read_u32(memory, desc_addr + 0x04);
    uint32_t bias_ptr = read_u32(memory, desc_addr + 0x08);
    uint32_t output_ptr = read_u32(memory, desc_addr + 0x0C);
    uint32_t input_len = read_u32(memory, desc_addr + 0x10);
    uint32_t output_len = read_u32(memory, desc_addr + 0x14);
    uint32_t flags = read_u32(memory, desc_addr + 0x18);
    uint32_t reserved = read_u32(memory, desc_addr + 0x1C);
    
    // Validate
    if (flags != 0 || reserved != 0) return ERR_INVALID_PTR;
    if (input_len == 0 || output_len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(input_ptr, 4) || !is_aligned(weights_ptr, 4) ||
        !is_aligned(bias_ptr, 4) || !is_aligned(output_ptr, 4)) {
        return ERR_UNALIGNED;
    }
    
    uint32_t input_size = 0;
    uint32_t weights_size = 0;
    uint32_t bias_size = 0;
    uint32_t output_size = 0;
    if (!compute_matvec_sizes(input_len, output_len, &input_size, &weights_size, &bias_size, &output_size)) {
        return ERR_INVALID_PTR;
    }
    
    if (!is_valid_ptr(memory, input_ptr, input_size) ||
        !is_valid_ptr(memory, weights_ptr, weights_size) ||
        !is_valid_ptr(memory, bias_ptr, bias_size) ||
        !is_valid_ptr(memory, output_ptr, output_size)) {
        return ERR_INVALID_PTR;
    }
    
    // Compute: out[j] = bias[j] + sum(i) input[i] * weight[i*output_len+j]
    for (uint32_t j = 0; j < output_len; ++j) {
        float acc = read_f32(memory, bias_ptr + j * 4);
        for (uint32_t i = 0; i < input_len; ++i) {
            float inp = read_f32(memory, input_ptr + i * 4);
            float w = read_f32(memory, weights_ptr + (i * output_len + j) * 4);
            acc = acc + inp * w;  // Float arithmetic, native rounding
        }
        write_f32(const_cast<std::vector<uint8_t>&>(memory), output_ptr + j * 4, acc);
    }
    
    return ERR_OK;
}

// NVRELU.F32 implementation
uint32_t NeuralOps::vec_relu_f32(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr,
    uint32_t src_ptr,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(dst_ptr, 4) || !is_aligned(src_ptr, 4)) {
        return ERR_UNALIGNED;
    }
    
    uint32_t size = len * 4;
    if (!is_valid_ptr(memory, dst_ptr, size) || !is_valid_ptr(memory, src_ptr, size)) {
        return ERR_INVALID_PTR;
    }
    
    for (uint32_t i = 0; i < len; ++i) {
        float x = read_f32(memory, src_ptr + i * 4);
        float y = (x > 0.0f) ? x : 0.0f;
        write_f32(memory, dst_ptr + i * 4, y);
    }
    
    return ERR_OK;
}

// NVSIGPWL.F32 implementation
uint32_t NeuralOps::vec_sigmoid_pwl_f32(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr,
    uint32_t src_ptr,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(dst_ptr, 4) || !is_aligned(src_ptr, 4)) {
        return ERR_UNALIGNED;
    }
    
    uint32_t size = len * 4;
    if (!is_valid_ptr(memory, dst_ptr, size) || !is_valid_ptr(memory, src_ptr, size)) {
        return ERR_INVALID_PTR;
    }
    
    for (uint32_t i = 0; i < len; ++i) {
        float x = read_f32(memory, src_ptr + i * 4);
        float y;
        if (x <= -4.0f) {
            y = 0.0f;
        } else if (x >= 4.0f) {
            y = 1.0f;
        } else {
            y = 0.5f + x * 0.125f;
        }
        write_f32(memory, dst_ptr + i * 4, y);
    }
    
    return ERR_OK;
}

// NVCLAMPU8.F32 implementation
uint32_t NeuralOps::vec_clamp_scale_u8_f32(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr_u8,
    uint32_t src_ptr_f32,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(src_ptr_f32, 4)) {
        return ERR_UNALIGNED;
    }
    
    uint32_t f32_size = len * 4;
    if (!is_valid_ptr(memory, src_ptr_f32, f32_size) ||
        !is_valid_ptr(memory, dst_ptr_u8, len)) {
        return ERR_INVALID_PTR;
    }
    
    for (uint32_t i = 0; i < len; ++i) {
        float x = read_f32(memory, src_ptr_f32 + i * 4);
        
        // Handle NaN
        if (std::isnan(x)) {
            x = 0.0f;
        }
        
        // Clamp to [0, 1]
        if (x < 0.0f) x = 0.0f;
        if (x > 1.0f) x = 1.0f;
        
        // Scale by 255 and truncate
        float scaled = x * 255.0f;
        uint32_t ival = static_cast<uint32_t>(scaled);
        if (ival > 255) ival = 255;
        
        memory[dst_ptr_u8 + i] = static_cast<uint8_t>(ival);
    }
    
    return ERR_OK;
}

// ============================================================================
// CUSTOM3 (0x7B) enhanced kernels
//
// These paths keep fail-loud validation identical to v1 but use slightly more
// cache-friendly loop ordering for matvec and explicit chunking for vector ops.
// Semantics must remain identical to v1 kernels.
// ============================================================================

uint32_t NeuralOps::matvec_f32_v2(
    std::vector<uint8_t>& memory,
    uint32_t desc_addr
) {
    if (!is_valid_ptr(memory, desc_addr, 32)) {
        return ERR_INVALID_PTR;
    }

    const uint32_t input_ptr = read_u32(memory, desc_addr + 0x00);
    const uint32_t weights_ptr = read_u32(memory, desc_addr + 0x04);
    const uint32_t bias_ptr = read_u32(memory, desc_addr + 0x08);
    const uint32_t output_ptr = read_u32(memory, desc_addr + 0x0C);
    const uint32_t input_len = read_u32(memory, desc_addr + 0x10);
    const uint32_t output_len = read_u32(memory, desc_addr + 0x14);
    const uint32_t flags = read_u32(memory, desc_addr + 0x18);
    const uint32_t reserved = read_u32(memory, desc_addr + 0x1C);

    if (flags != 0 || reserved != 0) return ERR_INVALID_PTR;
    if (input_len == 0 || output_len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(input_ptr, 4) || !is_aligned(weights_ptr, 4) ||
        !is_aligned(bias_ptr, 4) || !is_aligned(output_ptr, 4)) {
        return ERR_UNALIGNED;
    }

    uint32_t input_size = 0;
    uint32_t weights_size = 0;
    uint32_t bias_size = 0;
    uint32_t output_size = 0;
    if (!compute_matvec_sizes(input_len, output_len, &input_size, &weights_size, &bias_size, &output_size)) {
        return ERR_INVALID_PTR;
    }

    if (!is_valid_ptr(memory, input_ptr, input_size) ||
        !is_valid_ptr(memory, weights_ptr, weights_size) ||
        !is_valid_ptr(memory, bias_ptr, bias_size) ||
        !is_valid_ptr(memory, output_ptr, output_size)) {
        return ERR_INVALID_PTR;
    }

    // Initialize output from bias once, then accumulate by input row.
    for (uint32_t j = 0; j < output_len; ++j) {
        write_f32(memory, output_ptr + j * 4, read_f32(memory, bias_ptr + j * 4));
    }

    for (uint32_t i = 0; i < input_len; ++i) {
        const float inp = read_f32(memory, input_ptr + i * 4);
        const uint32_t w_row = weights_ptr + (i * output_len * 4);

        // 4-lane unroll in software model to mirror planned RTL lane grouping.
        uint32_t j = 0;
        for (; j + 3 < output_len; j += 4) {
            const float w0 = read_f32(memory, w_row + (j + 0) * 4);
            const float w1 = read_f32(memory, w_row + (j + 1) * 4);
            const float w2 = read_f32(memory, w_row + (j + 2) * 4);
            const float w3 = read_f32(memory, w_row + (j + 3) * 4);

            const float o0 = read_f32(memory, output_ptr + (j + 0) * 4) + inp * w0;
            const float o1 = read_f32(memory, output_ptr + (j + 1) * 4) + inp * w1;
            const float o2 = read_f32(memory, output_ptr + (j + 2) * 4) + inp * w2;
            const float o3 = read_f32(memory, output_ptr + (j + 3) * 4) + inp * w3;

            write_f32(memory, output_ptr + (j + 0) * 4, o0);
            write_f32(memory, output_ptr + (j + 1) * 4, o1);
            write_f32(memory, output_ptr + (j + 2) * 4, o2);
            write_f32(memory, output_ptr + (j + 3) * 4, o3);
        }
        for (; j < output_len; ++j) {
            const float w = read_f32(memory, w_row + j * 4);
            const float o = read_f32(memory, output_ptr + j * 4) + inp * w;
            write_f32(memory, output_ptr + j * 4, o);
        }
    }

    return ERR_OK;
}

uint32_t NeuralOps::matvec_f32_v2_lane4(
    std::vector<uint8_t>& memory,
    uint32_t desc_addr
) {
    return matvec_f32_v2(memory, desc_addr);
}

uint32_t NeuralOps::matvec_f32_v2_lane8(
    std::vector<uint8_t>& memory,
    uint32_t desc_addr
) {
    if (!is_valid_ptr(memory, desc_addr, 32)) {
        return ERR_INVALID_PTR;
    }

    const uint32_t input_ptr = read_u32(memory, desc_addr + 0x00);
    const uint32_t weights_ptr = read_u32(memory, desc_addr + 0x04);
    const uint32_t bias_ptr = read_u32(memory, desc_addr + 0x08);
    const uint32_t output_ptr = read_u32(memory, desc_addr + 0x0C);
    const uint32_t input_len = read_u32(memory, desc_addr + 0x10);
    const uint32_t output_len = read_u32(memory, desc_addr + 0x14);
    const uint32_t flags = read_u32(memory, desc_addr + 0x18);
    const uint32_t reserved = read_u32(memory, desc_addr + 0x1C);

    if (flags != 0 || reserved != 0) return ERR_INVALID_PTR;
    if (input_len == 0 || output_len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(input_ptr, 4) || !is_aligned(weights_ptr, 4) ||
        !is_aligned(bias_ptr, 4) || !is_aligned(output_ptr, 4)) {
        return ERR_UNALIGNED;
    }

    uint32_t input_size = 0;
    uint32_t weights_size = 0;
    uint32_t bias_size = 0;
    uint32_t output_size = 0;
    if (!compute_matvec_sizes(input_len, output_len, &input_size, &weights_size, &bias_size, &output_size)) {
        return ERR_INVALID_PTR;
    }

    if (!is_valid_ptr(memory, input_ptr, input_size) ||
        !is_valid_ptr(memory, weights_ptr, weights_size) ||
        !is_valid_ptr(memory, bias_ptr, bias_size) ||
        !is_valid_ptr(memory, output_ptr, output_size)) {
        return ERR_INVALID_PTR;
    }

    for (uint32_t j = 0; j < output_len; ++j) {
        write_f32(memory, output_ptr + j * 4, read_f32(memory, bias_ptr + j * 4));
    }

    for (uint32_t i = 0; i < input_len; ++i) {
        const float inp = read_f32(memory, input_ptr + i * 4);
        const uint32_t w_row = weights_ptr + (i * output_len * 4);

        uint32_t j = 0;
        for (; j + 7 < output_len; j += 8) {
            const float w0 = read_f32(memory, w_row + (j + 0) * 4);
            const float w1 = read_f32(memory, w_row + (j + 1) * 4);
            const float w2 = read_f32(memory, w_row + (j + 2) * 4);
            const float w3 = read_f32(memory, w_row + (j + 3) * 4);
            const float w4 = read_f32(memory, w_row + (j + 4) * 4);
            const float w5 = read_f32(memory, w_row + (j + 5) * 4);
            const float w6 = read_f32(memory, w_row + (j + 6) * 4);
            const float w7 = read_f32(memory, w_row + (j + 7) * 4);

            const float o0 = read_f32(memory, output_ptr + (j + 0) * 4) + inp * w0;
            const float o1 = read_f32(memory, output_ptr + (j + 1) * 4) + inp * w1;
            const float o2 = read_f32(memory, output_ptr + (j + 2) * 4) + inp * w2;
            const float o3 = read_f32(memory, output_ptr + (j + 3) * 4) + inp * w3;
            const float o4 = read_f32(memory, output_ptr + (j + 4) * 4) + inp * w4;
            const float o5 = read_f32(memory, output_ptr + (j + 5) * 4) + inp * w5;
            const float o6 = read_f32(memory, output_ptr + (j + 6) * 4) + inp * w6;
            const float o7 = read_f32(memory, output_ptr + (j + 7) * 4) + inp * w7;

            write_f32(memory, output_ptr + (j + 0) * 4, o0);
            write_f32(memory, output_ptr + (j + 1) * 4, o1);
            write_f32(memory, output_ptr + (j + 2) * 4, o2);
            write_f32(memory, output_ptr + (j + 3) * 4, o3);
            write_f32(memory, output_ptr + (j + 4) * 4, o4);
            write_f32(memory, output_ptr + (j + 5) * 4, o5);
            write_f32(memory, output_ptr + (j + 6) * 4, o6);
            write_f32(memory, output_ptr + (j + 7) * 4, o7);
        }
        for (; j < output_len; ++j) {
            const float w = read_f32(memory, w_row + j * 4);
            const float o = read_f32(memory, output_ptr + j * 4) + inp * w;
            write_f32(memory, output_ptr + j * 4, o);
        }
    }

    return ERR_OK;
}

uint32_t NeuralOps::vec_relu_f32_v2(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr,
    uint32_t src_ptr,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(dst_ptr, 4) || !is_aligned(src_ptr, 4)) return ERR_UNALIGNED;

    const uint32_t size = len * 4;
    if (!is_valid_ptr(memory, dst_ptr, size) || !is_valid_ptr(memory, src_ptr, size)) {
        return ERR_INVALID_PTR;
    }

    uint32_t i = 0;
    for (; i + 3 < len; i += 4) {
        const float x0 = read_f32(memory, src_ptr + (i + 0) * 4);
        const float x1 = read_f32(memory, src_ptr + (i + 1) * 4);
        const float x2 = read_f32(memory, src_ptr + (i + 2) * 4);
        const float x3 = read_f32(memory, src_ptr + (i + 3) * 4);
        write_f32(memory, dst_ptr + (i + 0) * 4, (x0 > 0.0f) ? x0 : 0.0f);
        write_f32(memory, dst_ptr + (i + 1) * 4, (x1 > 0.0f) ? x1 : 0.0f);
        write_f32(memory, dst_ptr + (i + 2) * 4, (x2 > 0.0f) ? x2 : 0.0f);
        write_f32(memory, dst_ptr + (i + 3) * 4, (x3 > 0.0f) ? x3 : 0.0f);
    }
    for (; i < len; ++i) {
        const float x = read_f32(memory, src_ptr + i * 4);
        write_f32(memory, dst_ptr + i * 4, (x > 0.0f) ? x : 0.0f);
    }
    return ERR_OK;
}

uint32_t NeuralOps::vec_sigmoid_pwl_f32_v2(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr,
    uint32_t src_ptr,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(dst_ptr, 4) || !is_aligned(src_ptr, 4)) return ERR_UNALIGNED;

    const uint32_t size = len * 4;
    if (!is_valid_ptr(memory, dst_ptr, size) || !is_valid_ptr(memory, src_ptr, size)) {
        return ERR_INVALID_PTR;
    }

    auto sigmoid_pwl = [](float x) {
        if (x <= -4.0f) return 0.0f;
        if (x >= 4.0f) return 1.0f;
        return 0.5f + x * 0.125f;
    };

    uint32_t i = 0;
    for (; i + 3 < len; i += 4) {
        write_f32(memory, dst_ptr + (i + 0) * 4, sigmoid_pwl(read_f32(memory, src_ptr + (i + 0) * 4)));
        write_f32(memory, dst_ptr + (i + 1) * 4, sigmoid_pwl(read_f32(memory, src_ptr + (i + 1) * 4)));
        write_f32(memory, dst_ptr + (i + 2) * 4, sigmoid_pwl(read_f32(memory, src_ptr + (i + 2) * 4)));
        write_f32(memory, dst_ptr + (i + 3) * 4, sigmoid_pwl(read_f32(memory, src_ptr + (i + 3) * 4)));
    }
    for (; i < len; ++i) {
        write_f32(memory, dst_ptr + i * 4, sigmoid_pwl(read_f32(memory, src_ptr + i * 4)));
    }
    return ERR_OK;
}

uint32_t NeuralOps::vec_clamp_scale_u8_f32_v2(
    std::vector<uint8_t>& memory,
    uint32_t dst_ptr_u8,
    uint32_t src_ptr_f32,
    uint32_t len
) {
    if (len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(src_ptr_f32, 4)) return ERR_UNALIGNED;

    const uint32_t f32_size = len * 4;
    if (!is_valid_ptr(memory, src_ptr_f32, f32_size) || !is_valid_ptr(memory, dst_ptr_u8, len)) {
        return ERR_INVALID_PTR;
    }

    for (uint32_t i = 0; i < len; ++i) {
        float x = read_f32(memory, src_ptr_f32 + i * 4);
        if (std::isnan(x)) x = 0.0f;
        if (x < 0.0f) x = 0.0f;
        if (x > 1.0f) x = 1.0f;
        const float scaled = x * 255.0f;
        uint32_t ival = static_cast<uint32_t>(scaled);
        if (ival > 255) ival = 255;
        memory[dst_ptr_u8 + i] = static_cast<uint8_t>(ival);
    }
    return ERR_OK;
}
