#include <gtest/gtest.h>
#include "NeuralOps.h"
#include <cmath>
#include <cstring>

// Test fixture for neural ops
class NeuralOpsTest : public ::testing::Test {
protected:
    // Allocate a large memory buffer for testing
    std::vector<uint8_t> memory;
    
    void SetUp() override {
        // Allocate 1 MB of memory for test data
        memory.resize(1024 * 1024, 0);
    }
    
    void write_f32(uint32_t addr, float val) {
        uint32_t bits;
        std::memcpy(&bits, &val, 4);
        std::memcpy(&memory[addr], &bits, 4);
    }
    
    float read_f32(uint32_t addr) {
        uint32_t bits;
        std::memcpy(&bits, &memory[addr], 4);
        float val;
        std::memcpy(&val, &bits, 4);
        return val;
    }
    
    void write_u32(uint32_t addr, uint32_t val) {
        std::memcpy(&memory[addr], &val, 4);
    }
    
    uint32_t read_u32(uint32_t addr) {
        uint32_t val;
        std::memcpy(&val, &memory[addr], 4);
        return val;
    }
};

// ============================================================================
// NMATVEC.F32 Tests
// ============================================================================

TEST_F(NeuralOpsTest, MatvecBasic2x2) {
    // Simple 2x2 matrix, 2-element vector
    // input = [1, 2]
    // weights = [1, 2, 3, 4] (row-major: 2x2 = 2 outputs, 2 inputs)
    //   out[0] = 1*1 + 2*3 = 7
    //   out[1] = 1*2 + 2*4 = 10
    // bias = [0, 0]
    
    uint32_t input_ptr = 0x1000;
    uint32_t weights_ptr = 0x1100;
    uint32_t bias_ptr = 0x1200;
    uint32_t output_ptr = 0x1300;
    uint32_t desc_ptr = 0x0;
    
    write_f32(input_ptr + 0, 1.0f);
    write_f32(input_ptr + 4, 2.0f);
    
    write_f32(weights_ptr + 0, 1.0f);   // weight[0,0]
    write_f32(weights_ptr + 4, 2.0f);   // weight[0,1]
    write_f32(weights_ptr + 8, 3.0f);   // weight[1,0]
    write_f32(weights_ptr + 12, 4.0f);  // weight[1,1]
    
    write_f32(bias_ptr + 0, 0.0f);
    write_f32(bias_ptr + 4, 0.0f);
    
    // Write descriptor
    write_u32(desc_ptr + 0x00, input_ptr);
    write_u32(desc_ptr + 0x04, weights_ptr);
    write_u32(desc_ptr + 0x08, bias_ptr);
    write_u32(desc_ptr + 0x0C, output_ptr);
    write_u32(desc_ptr + 0x10, 2);      // input_len
    write_u32(desc_ptr + 0x14, 2);      // output_len
    write_u32(desc_ptr + 0x18, 0);      // flags
    
    uint32_t err = NeuralOps::matvec_f32(memory, desc_ptr);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(output_ptr + 0), 7.0f);
    EXPECT_FLOAT_EQ(read_f32(output_ptr + 4), 10.0f);
}

TEST_F(NeuralOpsTest, MatvecWithBias) {
    // Test that bias is correctly added
    uint32_t input_ptr = 0x1000;
    uint32_t weights_ptr = 0x1100;
    uint32_t bias_ptr = 0x1200;
    uint32_t output_ptr = 0x1300;
    uint32_t desc_ptr = 0x0;
    
    write_f32(input_ptr + 0, 1.0f);
    
    write_f32(weights_ptr + 0, 2.0f);   // weight[0,0]
    write_f32(weights_ptr + 4, 3.0f);   // weight[0,1]
    
    write_f32(bias_ptr + 0, 5.0f);
    write_f32(bias_ptr + 4, 7.0f);
    
    write_u32(desc_ptr + 0x00, input_ptr);
    write_u32(desc_ptr + 0x04, weights_ptr);
    write_u32(desc_ptr + 0x08, bias_ptr);
    write_u32(desc_ptr + 0x0C, output_ptr);
    write_u32(desc_ptr + 0x10, 1);      // input_len
    write_u32(desc_ptr + 0x14, 2);      // output_len
    write_u32(desc_ptr + 0x18, 0);      // flags
    
    uint32_t err = NeuralOps::matvec_f32(memory, desc_ptr);
    EXPECT_EQ(err, 0);
    
    // out[0] = 5 + 1*2 = 7
    // out[1] = 7 + 1*3 = 10
    EXPECT_FLOAT_EQ(read_f32(output_ptr + 0), 7.0f);
    EXPECT_FLOAT_EQ(read_f32(output_ptr + 4), 10.0f);
}

TEST_F(NeuralOpsTest, MatvecInvalidDescriptor) {
    uint32_t desc_ptr = memory.size() + 100;  // Out of bounds
    uint32_t err = NeuralOps::matvec_f32(memory, desc_ptr);
    EXPECT_EQ(err, NeuralOps::ERR_INVALID_PTR);
}

TEST_F(NeuralOpsTest, MatvecZeroLength) {
    uint32_t desc_ptr = 0x0;
    
    write_u32(desc_ptr + 0x00, 0x2000);
    write_u32(desc_ptr + 0x04, 0x2100);
    write_u32(desc_ptr + 0x08, 0x2200);
    write_u32(desc_ptr + 0x0C, 0x2300);
    write_u32(desc_ptr + 0x10, 0);      // input_len = 0
    write_u32(desc_ptr + 0x14, 2);      // output_len
    write_u32(desc_ptr + 0x18, 0);      // flags
    
    uint32_t err = NeuralOps::matvec_f32(memory, desc_ptr);
    EXPECT_EQ(err, NeuralOps::ERR_INVALID_LEN);
}

TEST_F(NeuralOpsTest, MatvecUnaligned) {
    uint32_t desc_ptr = 0x0;
    
    write_u32(desc_ptr + 0x00, 0x2001);  // Misaligned input
    write_u32(desc_ptr + 0x04, 0x2100);
    write_u32(desc_ptr + 0x08, 0x2200);
    write_u32(desc_ptr + 0x0C, 0x2300);
    write_u32(desc_ptr + 0x10, 2);
    write_u32(desc_ptr + 0x14, 2);
    write_u32(desc_ptr + 0x18, 0);
    
    uint32_t err = NeuralOps::matvec_f32(memory, desc_ptr);
    EXPECT_EQ(err, NeuralOps::ERR_UNALIGNED);
}

// ============================================================================
// NVRELU.F32 Tests
// ============================================================================

TEST_F(NeuralOpsTest, ReluBasic) {
    uint32_t src_ptr = 0x3000;
    uint32_t dst_ptr = 0x3100;
    
    write_f32(src_ptr + 0, -2.0f);
    write_f32(src_ptr + 4, 0.0f);
    write_f32(src_ptr + 8, 1.5f);
    write_f32(src_ptr + 12, -0.5f);
    
    uint32_t err = NeuralOps::vec_relu_f32(memory, dst_ptr, src_ptr, 4);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 0), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 4), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 8), 1.5f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 12), 0.0f);
}

TEST_F(NeuralOpsTest, ReluInPlace) {
    uint32_t ptr = 0x4000;
    
    write_f32(ptr + 0, -1.0f);
    write_f32(ptr + 4, 2.0f);
    write_f32(ptr + 8, -3.0f);
    
    uint32_t err = NeuralOps::vec_relu_f32(memory, ptr, ptr, 3);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(ptr + 0), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(ptr + 4), 2.0f);
    EXPECT_FLOAT_EQ(read_f32(ptr + 8), 0.0f);
}

TEST_F(NeuralOpsTest, ReluUnaligned) {
    uint32_t src_ptr = 0x5001;  // Misaligned
    uint32_t dst_ptr = 0x5100;
    
    uint32_t err = NeuralOps::vec_relu_f32(memory, dst_ptr, src_ptr, 1);
    EXPECT_EQ(err, NeuralOps::ERR_UNALIGNED);
}

TEST_F(NeuralOpsTest, ReluInvalidLength) {
    uint32_t src_ptr = 0x5000;
    uint32_t dst_ptr = 0x5100;
    
    uint32_t err = NeuralOps::vec_relu_f32(memory, dst_ptr, src_ptr, 0);
    EXPECT_EQ(err, NeuralOps::ERR_INVALID_LEN);
}

// ============================================================================
// NVSIGPWL.F32 Tests
// ============================================================================

TEST_F(NeuralOpsTest, SigmoidPWLBasic) {
    uint32_t src_ptr = 0x6000;
    uint32_t dst_ptr = 0x6100;
    
    // Test across the piecewise boundaries
    write_f32(src_ptr + 0, -5.0f);   // < -4 -> 0
    write_f32(src_ptr + 4, -4.0f);   // = -4 -> 0
    write_f32(src_ptr + 8, -2.0f);   // -4 < x < 4 -> 0.5 + (-2)*0.125 = 0.25
    write_f32(src_ptr + 12, 0.0f);   // = 0 -> 0.5
    write_f32(src_ptr + 16, 2.0f);   // 0 < x < 4 -> 0.5 + 2*0.125 = 0.75
    write_f32(src_ptr + 20, 4.0f);   // = 4 -> 1
    write_f32(src_ptr + 24, 5.0f);   // > 4 -> 1
    
    uint32_t err = NeuralOps::vec_sigmoid_pwl_f32(memory, dst_ptr, src_ptr, 7);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 0), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 4), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 8), 0.25f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 12), 0.5f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 16), 0.75f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 20), 1.0f);
    EXPECT_FLOAT_EQ(read_f32(dst_ptr + 24), 1.0f);
}

TEST_F(NeuralOpsTest, SigmoidPWLInPlace) {
    uint32_t ptr = 0x7000;
    
    write_f32(ptr + 0, -3.0f);
    write_f32(ptr + 4, 0.0f);
    
    uint32_t err = NeuralOps::vec_sigmoid_pwl_f32(memory, ptr, ptr, 2);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(ptr + 0), 0.5f + (-3.0f) * 0.125f);
    EXPECT_FLOAT_EQ(read_f32(ptr + 4), 0.5f);
}

// ============================================================================
// NVCLAMPU8.F32 Tests
// ============================================================================

TEST_F(NeuralOpsTest, ClampU8Basic) {
    uint32_t src_ptr = 0x8000;
    uint32_t dst_ptr = 0x8100;
    
    write_f32(src_ptr + 0, 0.0f);     // -> 0
    write_f32(src_ptr + 4, 0.5f);     // -> 127 (0.5*255)
    write_f32(src_ptr + 8, 1.0f);     // -> 255
    write_f32(src_ptr + 12, -0.5f);   // clamped to 0
    write_f32(src_ptr + 16, 1.5f);    // clamped to 255
    
    uint32_t err = NeuralOps::vec_clamp_scale_u8_f32(memory, dst_ptr, src_ptr, 5);
    EXPECT_EQ(err, 0);
    
    EXPECT_EQ(memory[dst_ptr + 0], 0);
    EXPECT_EQ(memory[dst_ptr + 1], 127);  // 0.5*255 = 127.5 -> 127
    EXPECT_EQ(memory[dst_ptr + 2], 255);
    EXPECT_EQ(memory[dst_ptr + 3], 0);    // Clamped
    EXPECT_EQ(memory[dst_ptr + 4], 255);  // Clamped
}

TEST_F(NeuralOpsTest, ClampU8NaN) {
    uint32_t src_ptr = 0x8000;
    uint32_t dst_ptr = 0x8100;
    
    // Write a NaN (sign bit 0, exponent all 1s, mantissa non-zero)
    uint32_t nan_bits = 0x7FC00001;
    std::memcpy(&memory[src_ptr], &nan_bits, 4);
    
    uint32_t err = NeuralOps::vec_clamp_scale_u8_f32(memory, dst_ptr, src_ptr, 1);
    EXPECT_EQ(err, 0);
    EXPECT_EQ(memory[dst_ptr], 0);  // NaN -> 0
}

TEST_F(NeuralOpsTest, ClampU8Unaligned) {
    uint32_t src_ptr = 0x9001;  // Misaligned
    uint32_t dst_ptr = 0x9100;
    
    uint32_t err = NeuralOps::vec_clamp_scale_u8_f32(memory, dst_ptr, src_ptr, 1);
    EXPECT_EQ(err, NeuralOps::ERR_UNALIGNED);
}

TEST_F(NeuralOpsTest, ClampU8InvalidLength) {
    uint32_t src_ptr = 0x9000;
    uint32_t dst_ptr = 0x9100;
    
    uint32_t err = NeuralOps::vec_clamp_scale_u8_f32(memory, dst_ptr, src_ptr, 0);
    EXPECT_EQ(err, NeuralOps::ERR_INVALID_LEN);
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST_F(NeuralOpsTest, PipelineReluToSigmoid) {
    // Test chaining relu -> sigmoid as would happen in neural layer
    uint32_t data_ptr = 0xA000;
    uint32_t temp_ptr = 0xA100;
    
    write_f32(data_ptr + 0, -1.0f);
    write_f32(data_ptr + 4, 0.5f);
    write_f32(data_ptr + 8, 2.0f);
    
    // Apply ReLU in-place
    uint32_t err = NeuralOps::vec_relu_f32(memory, data_ptr, data_ptr, 3);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 0), 0.0f);
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 4), 0.5f);
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 8), 2.0f);
    
    // Apply sigmoid
    err = NeuralOps::vec_sigmoid_pwl_f32(memory, data_ptr, data_ptr, 3);
    EXPECT_EQ(err, 0);
    
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 0), 0.5f);  // sigmoid(0)
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 4), 0.5625f);  // sigmoid(0.5)
    EXPECT_FLOAT_EQ(read_f32(data_ptr + 8), 0.75f);  // sigmoid(2.0)
}

TEST_F(NeuralOpsTest, MatvecV2MatchesV1) {
    std::vector<uint8_t> mem_v1 = memory;
    std::vector<uint8_t> mem_v2 = memory;

    const uint32_t input_ptr = 0x1000;
    const uint32_t weights_ptr = 0x1100;
    const uint32_t bias_ptr = 0x1200;
    const uint32_t output_ptr = 0x1300;
    const uint32_t desc_ptr = 0x0;

    auto init_mem = [&](std::vector<uint8_t>& mem) {
        auto write_u32_local = [&](uint32_t addr, uint32_t val) { std::memcpy(&mem[addr], &val, 4); };
        auto write_f32_local = [&](uint32_t addr, float val) {
            uint32_t bits;
            std::memcpy(&bits, &val, 4);
            std::memcpy(&mem[addr], &bits, 4);
        };

        write_f32_local(input_ptr + 0, 1.0f);
        write_f32_local(input_ptr + 4, 2.0f);

        write_f32_local(weights_ptr + 0, 1.0f);
        write_f32_local(weights_ptr + 4, 2.0f);
        write_f32_local(weights_ptr + 8, 3.0f);
        write_f32_local(weights_ptr + 12, 4.0f);

        write_f32_local(bias_ptr + 0, 0.0f);
        write_f32_local(bias_ptr + 4, 0.0f);

        write_u32_local(desc_ptr + 0x00, input_ptr);
        write_u32_local(desc_ptr + 0x04, weights_ptr);
        write_u32_local(desc_ptr + 0x08, bias_ptr);
        write_u32_local(desc_ptr + 0x0C, output_ptr);
        write_u32_local(desc_ptr + 0x10, 2);
        write_u32_local(desc_ptr + 0x14, 2);
        write_u32_local(desc_ptr + 0x18, 0);
    };

    init_mem(mem_v1);
    init_mem(mem_v2);

    const uint32_t err_v1 = NeuralOps::matvec_f32(mem_v1, desc_ptr);
    const uint32_t err_v2 = NeuralOps::matvec_f32_v2(mem_v2, desc_ptr);
    EXPECT_EQ(err_v1, NeuralOps::ERR_OK);
    EXPECT_EQ(err_v2, NeuralOps::ERR_OK);

    for (uint32_t j = 0; j < 2; ++j) {
        float a;
        float b;
        std::memcpy(&a, &mem_v1[output_ptr + j * 4], 4);
        std::memcpy(&b, &mem_v2[output_ptr + j * 4], 4);
        EXPECT_FLOAT_EQ(a, b);
    }
}

TEST_F(NeuralOpsTest, ReluV2MatchesV1) {
    std::vector<uint8_t> mem_v1 = memory;
    std::vector<uint8_t> mem_v2 = memory;
    const uint32_t src_ptr = 0x3000;
    const uint32_t dst_ptr = 0x3100;

    auto init_mem = [&](std::vector<uint8_t>& mem) {
        auto write_f32_local = [&](uint32_t addr, float val) {
            uint32_t bits;
            std::memcpy(&bits, &val, 4);
            std::memcpy(&mem[addr], &bits, 4);
        };
        write_f32_local(src_ptr + 0, -2.0f);
        write_f32_local(src_ptr + 4, 0.0f);
        write_f32_local(src_ptr + 8, 1.5f);
        write_f32_local(src_ptr + 12, -0.5f);
    };

    init_mem(mem_v1);
    init_mem(mem_v2);

    EXPECT_EQ(NeuralOps::vec_relu_f32(mem_v1, dst_ptr, src_ptr, 4), NeuralOps::ERR_OK);
    EXPECT_EQ(NeuralOps::vec_relu_f32_v2(mem_v2, dst_ptr, src_ptr, 4), NeuralOps::ERR_OK);

    for (uint32_t i = 0; i < 4; ++i) {
        float a;
        float b;
        std::memcpy(&a, &mem_v1[dst_ptr + i * 4], 4);
        std::memcpy(&b, &mem_v2[dst_ptr + i * 4], 4);
        EXPECT_FLOAT_EQ(a, b);
    }
}

TEST_F(NeuralOpsTest, SigmoidV2MatchesV1) {
    std::vector<uint8_t> mem_v1 = memory;
    std::vector<uint8_t> mem_v2 = memory;
    const uint32_t src_ptr = 0x6000;
    const uint32_t dst_ptr = 0x6100;

    auto init_mem = [&](std::vector<uint8_t>& mem) {
        auto write_f32_local = [&](uint32_t addr, float val) {
            uint32_t bits;
            std::memcpy(&bits, &val, 4);
            std::memcpy(&mem[addr], &bits, 4);
        };
        write_f32_local(src_ptr + 0, -5.0f);
        write_f32_local(src_ptr + 4, -4.0f);
        write_f32_local(src_ptr + 8, -2.0f);
        write_f32_local(src_ptr + 12, 0.0f);
        write_f32_local(src_ptr + 16, 2.0f);
        write_f32_local(src_ptr + 20, 4.0f);
        write_f32_local(src_ptr + 24, 5.0f);
    };

    init_mem(mem_v1);
    init_mem(mem_v2);

    EXPECT_EQ(NeuralOps::vec_sigmoid_pwl_f32(mem_v1, dst_ptr, src_ptr, 7), NeuralOps::ERR_OK);
    EXPECT_EQ(NeuralOps::vec_sigmoid_pwl_f32_v2(mem_v2, dst_ptr, src_ptr, 7), NeuralOps::ERR_OK);

    for (uint32_t i = 0; i < 7; ++i) {
        float a;
        float b;
        std::memcpy(&a, &mem_v1[dst_ptr + i * 4], 4);
        std::memcpy(&b, &mem_v2[dst_ptr + i * 4], 4);
        EXPECT_FLOAT_EQ(a, b);
    }
}

TEST_F(NeuralOpsTest, ClampV2MatchesV1) {
    std::vector<uint8_t> mem_v1 = memory;
    std::vector<uint8_t> mem_v2 = memory;
    const uint32_t src_ptr = 0x8000;
    const uint32_t dst_ptr = 0x8100;

    auto init_mem = [&](std::vector<uint8_t>& mem) {
        auto write_f32_local = [&](uint32_t addr, float val) {
            uint32_t bits;
            std::memcpy(&bits, &val, 4);
            std::memcpy(&mem[addr], &bits, 4);
        };
        write_f32_local(src_ptr + 0, 0.0f);
        write_f32_local(src_ptr + 4, 0.5f);
        write_f32_local(src_ptr + 8, 1.0f);
        write_f32_local(src_ptr + 12, -0.5f);
        write_f32_local(src_ptr + 16, 1.5f);
    };

    init_mem(mem_v1);
    init_mem(mem_v2);

    EXPECT_EQ(NeuralOps::vec_clamp_scale_u8_f32(mem_v1, dst_ptr, src_ptr, 5), NeuralOps::ERR_OK);
    EXPECT_EQ(NeuralOps::vec_clamp_scale_u8_f32_v2(mem_v2, dst_ptr, src_ptr, 5), NeuralOps::ERR_OK);

    for (uint32_t i = 0; i < 5; ++i) {
        EXPECT_EQ(mem_v1[dst_ptr + i], mem_v2[dst_ptr + i]);
    }
}
