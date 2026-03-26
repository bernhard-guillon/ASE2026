#include "NeuralOps.h"

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
    if (addr > mem.size()) return false;
    return (addr + size) <= mem.size();
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
    
    // Validate
    if (flags != 0) return ERR_INVALID_PTR;
    if (input_len == 0 || output_len == 0) return ERR_INVALID_LEN;
    if (!is_aligned(input_ptr, 4) || !is_aligned(weights_ptr, 4) ||
        !is_aligned(bias_ptr, 4) || !is_aligned(output_ptr, 4)) {
        return ERR_UNALIGNED;
    }
    
    uint32_t input_size = input_len * 4;
    uint32_t weights_size = input_len * output_len * 4;
    uint32_t bias_size = output_len * 4;
    uint32_t output_size = output_len * 4;
    
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
