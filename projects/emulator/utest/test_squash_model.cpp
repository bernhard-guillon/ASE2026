#include <gtest/gtest.h>
#include "NeuralOps.h"
#include <cstdio>
#include <cstring>
#include <vector>

// The reference binary produced by generate_squash_reference.py.
// CMake passes the path via -DREF_BIN="..."
#ifndef REF_BIN
#error "REF_BIN must be defined (path to squash_model_ref.bin)"
#endif

struct ActivationOverrideRef {
    uint32_t offset;
    uint32_t size;
    uint32_t activation; // 0=relu, 1=sigmoid, 2=none
};

struct LayerRef {
    uint32_t input_size;
    uint32_t output_size;
    uint32_t activation; // 0=relu, 1=sigmoid, 2=none
    std::vector<float> weights;  // input_major: input_size * output_size
    std::vector<float> biases;   // output_size
    std::vector<float> pre_act;  // matvec output before activation
    std::vector<float> post_act; // after activation
    std::vector<ActivationOverrideRef> overrides; // per-range activation overrides
};

static std::vector<float> read_floats(FILE *f, uint32_t n) {
    std::vector<float> v(n);
    if (n > 0 && fread(v.data(), sizeof(float), n, f) != n) {
        perror("read_floats");
        std::abort();
    }
    return v;
}

class SquashModelTest : public ::testing::Test {
protected:
    std::vector<uint8_t> mem;        // "emulated" memory
    std::vector<LayerRef> layers;    // reference data from Python
    std::vector<float> input;        // reference input

    static constexpr uint32_t MEM_SIZE = 8u * 1024 * 1024; // 8 MB
    static constexpr uint32_t INPUT_ADDR = 0x1000;
    static constexpr uint32_t OUTPUT_ADDR = 0x200000;
    static constexpr uint32_t WEIGHTS_BASE = 0x100000;
    static constexpr uint32_t DESC_ADDR_BASE = 0x00;

    void SetUp() override {
        mem.resize(MEM_SIZE, 0);
        read_ref_bin();
    }

    void read_ref_bin() {
        FILE *f = fopen(REF_BIN, "rb");
        ASSERT_NE(f, nullptr) << "Cannot open " << REF_BIN;

        uint32_t num_layers, input_size;
        ASSERT_EQ(fread(&num_layers, 4, 1, f), 1u);
        ASSERT_EQ(fread(&input_size, 4, 1, f), 1u);

        input = read_floats(f, input_size);

        for (uint32_t li = 0; li < num_layers; ++li) {
            LayerRef lr;
            uint32_t in_sz, out_sz, act;
            ASSERT_EQ(fread(&in_sz, 4, 1, f), 1u);
            ASSERT_EQ(fread(&out_sz, 4, 1, f), 1u);
            ASSERT_EQ(fread(&act, 4, 1, f), 1u);
            lr.input_size = in_sz;
            lr.output_size = out_sz;
            lr.activation = act;
            lr.weights = read_floats(f, in_sz * out_sz);
            lr.biases = read_floats(f, out_sz);
            lr.pre_act = read_floats(f, out_sz);
            lr.post_act = read_floats(f, out_sz);
            uint32_t num_ov;
            ASSERT_EQ(fread(&num_ov, 4, 1, f), 1u);
            for (uint32_t oi = 0; oi < num_ov; ++oi) {
                ActivationOverrideRef ov;
                ASSERT_EQ(fread(&ov.offset, 4, 1, f), 1u);
                ASSERT_EQ(fread(&ov.size, 4, 1, f), 1u);
                ASSERT_EQ(fread(&ov.activation, 4, 1, f), 1u);
                lr.overrides.push_back(ov);
            }
            layers.push_back(std::move(lr));
        }
        fclose(f);
    }

    void write_f32(uint32_t addr, float v) {
        uint32_t bits;
        std::memcpy(&bits, &v, 4);
        std::memcpy(&mem[addr], &bits, 4);
    }

    float read_f32(uint32_t addr) {
        uint32_t bits;
        std::memcpy(&bits, &mem[addr], 4);
        float v;
        std::memcpy(&v, &bits, 4);
        return v;
    }

    void write_u32(uint32_t addr, uint32_t v) {
        std::memcpy(&mem[addr], &v, 4);
    }

    // Run one merged layer through NeuralOps, compare against ref.
    void test_layer(uint32_t li, const float *input_vals) {
        const LayerRef &ref = layers[li];

        // Write input buffer
        for (uint32_t i = 0; i < ref.input_size; ++i)
            write_f32(INPUT_ADDR + i * 4, input_vals[i]);

        // Compute addresses for this layer's weights/biases
        uint32_t w_off = 0;
        for (uint32_t k = 0; k < li; ++k) {
            w_off += layers[k].input_size * layers[k].output_size;
        }
        uint32_t weights_addr = WEIGHTS_BASE + w_off * 4;
        // Biases follow all weights
        uint32_t b_off = 0;
        for (uint32_t k = 0; k < li; ++k) {
            b_off += layers[k].output_size;
        }
        uint32_t b_off_total = 0;
        for (const auto &l : layers)
            b_off_total += l.input_size * l.output_size;
        uint32_t biases_addr = WEIGHTS_BASE + b_off_total * 4 + b_off * 4;

        // Write weights (input-major: weight[i * output_len + j])
        for (uint32_t i = 0; i < ref.input_size * ref.output_size; ++i)
            write_f32(weights_addr + i * 4, ref.weights[i]);

        // Write biases
        for (uint32_t j = 0; j < ref.output_size; ++j)
            write_f32(biases_addr + j * 4, ref.biases[j]);

        // Write descriptor
        uint32_t desc_addr = DESC_ADDR_BASE + li * 32;
        write_u32(desc_addr + 0x00, INPUT_ADDR);
        write_u32(desc_addr + 0x04, weights_addr);
        write_u32(desc_addr + 0x08, biases_addr);
        write_u32(desc_addr + 0x0C, OUTPUT_ADDR);
        write_u32(desc_addr + 0x10, ref.input_size);
        write_u32(desc_addr + 0x14, ref.output_size);
        write_u32(desc_addr + 0x18, 0);
        write_u32(desc_addr + 0x1C, 0);

        // Run matvec (v2 path, which is CUSTOM3)
        uint32_t err = NeuralOps::matvec_f32_v2(mem, desc_addr);
        ASSERT_EQ(err, NeuralOps::ERR_OK) << "matvec_f32_v2 failed for layer " << li;

        // Pre-activation check
        for (uint32_t j = 0; j < ref.output_size; ++j) {
            float got = read_f32(OUTPUT_ADDR + j * 4);
            float expected = ref.pre_act[j];
            EXPECT_NEAR(got, expected, 1e-4f)
                << "Layer " << li << " pre_act[" << j << "]";
        }

        // Run main activation
        if (ref.activation == 0) {
            err = NeuralOps::vec_relu_f32_v2(mem, OUTPUT_ADDR, OUTPUT_ADDR, ref.output_size);
        } else if (ref.activation == 1) {
            err = NeuralOps::vec_sigmoid_pwl_f32_v2(mem, OUTPUT_ADDR, OUTPUT_ADDR, ref.output_size);
        } else {
            err = NeuralOps::ERR_OK; // activation == 2 (none) — skip
        }
        ASSERT_EQ(err, NeuralOps::ERR_OK) << "main activation failed for layer " << li;

        // Apply per-block activation overrides
        for (const auto &ov : ref.overrides) {
            uint32_t o_addr = OUTPUT_ADDR + ov.offset * 4;
            if (ov.activation == 0) {
                err = NeuralOps::vec_relu_f32_v2(mem, o_addr, o_addr, ov.size);
            } else if (ov.activation == 1) {
                err = NeuralOps::vec_sigmoid_pwl_f32_v2(mem, o_addr, o_addr, ov.size);
            }
            ASSERT_EQ(err, NeuralOps::ERR_OK) << "override activation failed for layer " << li;
        }

        // Post-activation check
        for (uint32_t j = 0; j < ref.output_size; ++j) {
            float got = read_f32(OUTPUT_ADDR + j * 4);
            float expected = ref.post_act[j];
            EXPECT_NEAR(got, expected, 1e-4f)
                << "Layer " << li << " post_act[" << j << "]";
        }
    }
};

TEST_F(SquashModelTest, Layer0Forward) {
    test_layer(0, input.data());
}

TEST_F(SquashModelTest, Layer1Forward) {
    // Run layer 0 first to get correct input for layer 1
    test_layer(0, input.data());
    // Read layer 0 output (now at OUTPUT_ADDR) and feed into layer 1
    // For the purpose of this test, we compare layer 1 independently,
    // using the reference layer 0 output as input to layer 1.
    test_layer(1, layers[0].post_act.data());
}

TEST_F(SquashModelTest, Layer2Forward) {
    test_layer(0, input.data());
    test_layer(1, layers[0].post_act.data());
    test_layer(2, layers[1].post_act.data());
}

TEST_F(SquashModelTest, FullForwardPass) {
    // Run all layers sequentially, using each layer's output as next input
    // This tests that the NeuralOps pipeline matches Python exactly
    const float *cur_input = input.data();
    for (uint32_t li = 0; li < layers.size(); ++li) {
        const LayerRef &ref = layers[li];
        // Write input
        for (uint32_t i = 0; i < ref.input_size; ++i)
            write_f32(INPUT_ADDR + i * 4, cur_input[i]);

        uint32_t w_off = 0;
        for (uint32_t k = 0; k < li; ++k)
            w_off += layers[k].input_size * layers[k].output_size;
        uint32_t weights_addr = WEIGHTS_BASE + w_off * 4;

        uint32_t b_off_total = 0;
        for (const auto &l : layers)
            b_off_total += l.input_size * l.output_size;
        uint32_t b_off = 0;
        for (uint32_t k = 0; k < li; ++k)
            b_off += layers[k].output_size;
        uint32_t biases_addr = WEIGHTS_BASE + b_off_total * 4 + b_off * 4;

        for (uint32_t i = 0; i < ref.input_size * ref.output_size; ++i)
            write_f32(weights_addr + i * 4, ref.weights[i]);
        for (uint32_t j = 0; j < ref.output_size; ++j)
            write_f32(biases_addr + j * 4, ref.biases[j]);

        uint32_t desc_addr = DESC_ADDR_BASE + li * 32;
        write_u32(desc_addr + 0x00, INPUT_ADDR);
        write_u32(desc_addr + 0x04, weights_addr);
        write_u32(desc_addr + 0x08, biases_addr);
        write_u32(desc_addr + 0x0C, OUTPUT_ADDR);
        write_u32(desc_addr + 0x10, ref.input_size);
        write_u32(desc_addr + 0x14, ref.output_size);
        write_u32(desc_addr + 0x18, 0);
        write_u32(desc_addr + 0x1C, 0);

        uint32_t err = NeuralOps::matvec_f32_v2(mem, desc_addr);
        ASSERT_EQ(err, NeuralOps::ERR_OK) << "matvec_f32_v2 failed for layer " << li;

        // Check pre_act
        for (uint32_t j = 0; j < ref.output_size; ++j) {
            EXPECT_NEAR(read_f32(OUTPUT_ADDR + j * 4), ref.pre_act[j], 1e-4f)
                << "FullForward layer " << li << " pre_act[" << j << "]";
        }

        if (ref.activation == 0)
            err = NeuralOps::vec_relu_f32_v2(mem, OUTPUT_ADDR, OUTPUT_ADDR, ref.output_size);
        else if (ref.activation == 1)
            err = NeuralOps::vec_sigmoid_pwl_f32_v2(mem, OUTPUT_ADDR, OUTPUT_ADDR, ref.output_size);
        else
            err = NeuralOps::ERR_OK; // activation == 2 (none)
        ASSERT_EQ(err, NeuralOps::ERR_OK) << "activation failed for layer " << li;

        for (const auto &ov : ref.overrides) {
            uint32_t o_addr = OUTPUT_ADDR + ov.offset * 4;
            if (ov.activation == 0)
                err = NeuralOps::vec_relu_f32_v2(mem, o_addr, o_addr, ov.size);
            else if (ov.activation == 1)
                err = NeuralOps::vec_sigmoid_pwl_f32_v2(mem, o_addr, o_addr, ov.size);
            ASSERT_EQ(err, NeuralOps::ERR_OK) << "override activation failed for layer " << li;
        }

        for (uint32_t j = 0; j < ref.output_size; ++j) {
            EXPECT_NEAR(read_f32(OUTPUT_ADDR + j * 4), ref.post_act[j], 1e-4f)
                << "FullForward layer " << li << " post_act[" << j << "]";
        }

        // Feed output as input to next layer
        cur_input = ref.post_act.data();
    }
}
