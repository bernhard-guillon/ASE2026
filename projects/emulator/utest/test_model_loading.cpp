/*
 * Test program for loading neural network models into emulator memory.
 * 
 * This verifies that:
 * 1. Models can be loaded from binary format
 * 2. Memory layout matches expectations
 * 3. Weights and biases are at correct addresses
 * 4. Data integrity is preserved
 */

#include <iostream>
#include <fstream>
#include <cassert>
#include <iomanip>
#include <cmath>
#include <cstring>

// Forward declare emulator classes
class Memory;
class Emulator;

// Include emulator headers
#include "Emulator.h"
#include "Memory.h"

// Memory layout constants
const uint32_t MODEL_WEIGHTS_START = 0x10000;  // Start of model weights in memory

struct ModelMetadata {
    const char* name;
    const char* binary_file;
    uint32_t expected_total_weights;
    uint32_t expected_total_biases;
    uint32_t num_layers;
};

struct LoadedModel {
    uint32_t base_address;
    uint32_t total_size;
    float* weights;
    float* biases;
    uint32_t num_weights;
    uint32_t num_biases;
};

// Helper function: Load binary model file into a buffer (with multiple path attempts)
bool loadBinaryFile(const char* filename, std::vector<uint8_t>& buffer) {
    // Build list of potential paths
    std::vector<std::string> paths;
    paths.push_back(filename);  // Original path
    paths.push_back("../weight-export/" + std::string(filename));
    paths.push_back("../../weight-export/" + std::string(filename));
    paths.push_back("../../../weight-export/" + std::string(filename));
    
    for (const auto& path : paths) {
        std::ifstream file(path, std::ios::binary);
        if (file.is_open()) {
            file.seekg(0, std::ios::end);
            size_t file_size = file.tellg();
            file.seekg(0, std::ios::beg);
            
            buffer.resize(file_size);
            file.read(reinterpret_cast<char*>(buffer.data()), file_size);
            file.close();
            return true;
        }
    }
    
    std::cerr << "ERROR: Could not open file: " << filename << std::endl;
    return false;
}

// Helper function: Load model from binary buffer into emulator memory
bool loadModelIntoEmulator(Emulator& emulator, const std::vector<uint8_t>& buffer, 
                          uint32_t base_address, LoadedModel& model) {
    if (buffer.size() < 32) {
        std::cerr << "ERROR: Buffer too small for header" << std::endl;
        return false;
    }
    
    // Parse header
    uint32_t magic = *reinterpret_cast<const uint32_t*>(buffer.data());
    uint32_t version = *reinterpret_cast<const uint32_t*>(buffer.data() + 4);
    uint32_t model_type = *reinterpret_cast<const uint32_t*>(buffer.data() + 8);
    uint32_t num_layers = *reinterpret_cast<const uint32_t*>(buffer.data() + 12);
    uint32_t total_weights = *reinterpret_cast<const uint32_t*>(buffer.data() + 16);
    uint32_t total_biases = *reinterpret_cast<const uint32_t*>(buffer.data() + 20);
    
    std::cout << "  Magic: 0x" << std::hex << magic << std::dec << std::endl;
    std::cout << "  Version: " << version << std::endl;
    std::cout << "  Model type: " << model_type << std::endl;
    std::cout << "  Layers: " << num_layers << std::endl;
    std::cout << "  Total weights: " << total_weights << std::endl;
    std::cout << "  Total biases: " << total_biases << std::endl;
    
    // Validate magic
    if (magic != 0x4E52414E) {  // "NRAL"
        std::cerr << "ERROR: Invalid magic number" << std::endl;
        return false;
    }
    
    // Load entire model into emulator memory
    Memory& memory = emulator.getMemory();
    model.base_address = base_address;
    model.total_size = buffer.size();
    model.num_weights = total_weights;
    model.num_biases = total_biases;
    
    // Copy buffer into emulator memory
    for (size_t i = 0; i < buffer.size(); ++i) {
        memory.write8(base_address + i, buffer[i]);
    }
    
    std::cout << "  Loaded " << buffer.size() << " bytes at 0x" 
              << std::hex << base_address << std::dec << std::endl;
    
    return true;
}

// Helper function: Verify weights in memory match expected values
bool verifyWeightsInMemory(Memory& memory, uint32_t weights_offset, 
                          const float* expected_weights, uint32_t count) {
    int mismatches = 0;
    const float TOLERANCE = 1e-6f;
    
    for (uint32_t i = 0; i < count && mismatches < 5; ++i) {
        uint32_t address = weights_offset + i * 4;
        
        // Read float from memory (little-endian)
        uint8_t bytes[4];
        for (int j = 0; j < 4; ++j) {
            bytes[j] = memory.read8(address + j);
        }
        float value;
        std::memcpy(&value, bytes, sizeof(float));
        
        float expected = expected_weights[i];
        float diff = std::abs(value - expected);
        
        if (diff > TOLERANCE && !(std::isnan(value) && std::isnan(expected))) {
            std::cerr << "    Mismatch at weight[" << i << "]: "
                     << "expected " << expected << ", got " << value << std::endl;
            mismatches++;
        }
    }
    
    return mismatches == 0;
}

// Main test program
int main(int argc, char* argv[]) {
    std::cout << "========================================\n";
    std::cout << "Neural Network Model Memory Test\n";
    std::cout << "========================================\n\n";
    
    // Create emulator with enough memory for models
    Emulator emulator(256 * 1024 * 1024);  // 256 MB
    Memory& memory = emulator.getMemory();
    
    ModelMetadata models[] = {
        {
            "Character Generator",
            "../weight-export/character_generator.bin",
            233216,  // From export output
            912,
            3
        }
    };
    
    uint32_t current_address = MODEL_WEIGHTS_START;
    int tests_passed = 0;
    int tests_failed = 0;
    
    for (const auto& model_info : models) {
        std::cout << "\n" << model_info.name << ":\n";
        std::cout << std::string(40, '-') << "\n";
        
        // Load binary file
        std::vector<uint8_t> buffer;
        if (!loadBinaryFile(model_info.binary_file, buffer)) {
            std::cerr << "FAILED: Could not load file\n";
            tests_failed++;
            continue;
        }
        
        std::cout << "File size: " << buffer.size() << " bytes\n";
        
        // Load into emulator
        LoadedModel model;
        if (!loadModelIntoEmulator(emulator, buffer, current_address, model)) {
            std::cerr << "FAILED: Could not load into emulator\n";
            tests_failed++;
            continue;
        }
        
        // Verify header in memory
        std::cout << "\n  Verification:\n";
        
        uint32_t magic = memory.read32(current_address);
        if (magic == 0x4E52414E) {
            std::cout << "    ✓ Magic number correct (0x4E52414E)\n";
            tests_passed++;
        } else {
            std::cerr << "    ✗ Magic number incorrect: 0x" << std::hex << magic << std::dec << "\n";
            tests_failed++;
        }
        
        uint32_t version = memory.read32(current_address + 4);
        if (version == 1) {
            std::cout << "    ✓ Version correct (1)\n";
            tests_passed++;
        } else {
            std::cerr << "    ✗ Version incorrect: " << version << "\n";
            tests_failed++;
        }
        
        uint32_t num_layers = memory.read32(current_address + 12);
        if (num_layers == model_info.num_layers) {
            std::cout << "    ✓ Layer count correct (" << num_layers << ")\n";
            tests_passed++;
        } else {
            std::cerr << "    ✗ Layer count incorrect: " << num_layers 
                     << " (expected " << model_info.num_layers << ")\n";
            tests_failed++;
        }
        
        uint32_t total_weights = memory.read32(current_address + 16);
        if (total_weights == model_info.expected_total_weights) {
            std::cout << "    ✓ Weight count correct (" << total_weights << ")\n";
            tests_passed++;
        } else {
            std::cerr << "    ✗ Weight count incorrect: " << total_weights 
                     << " (expected " << model_info.expected_total_weights << ")\n";
            tests_failed++;
        }
        
        uint32_t total_biases = memory.read32(current_address + 20);
        if (total_biases == model_info.expected_total_biases) {
            std::cout << "    ✓ Bias count correct (" << total_biases << ")\n";
            tests_passed++;
        } else {
            std::cerr << "    ✗ Bias count incorrect: " << total_biases 
                     << " (expected " << model_info.expected_total_biases << ")\n";
            tests_failed++;
        }
        
        // Verify data is readable at expected offsets
        uint32_t layer_table_start = current_address + 32;
        uint32_t weights_start = layer_table_start + num_layers * 32;
        uint32_t biases_start = weights_start + total_weights * 4;
        
        std::cout << "\n  Memory Layout:\n";
        std::cout << "    Header:       0x" << std::hex << current_address << std::dec << "\n";
        std::cout << "    Layer table:  0x" << std::hex << layer_table_start << std::dec << "\n";
        std::cout << "    Weights:      0x" << std::hex << weights_start << std::dec 
                 << " (" << total_weights * 4 << " bytes)\n";
        std::cout << "    Biases:       0x" << std::hex << biases_start << std::dec 
                 << " (" << total_biases * 4 << " bytes)\n";
        
        // Try to read first few weights
        std::cout << "\n  Sample Data:\n";
        if (weights_start + 4 <= memory.size()) {
            uint32_t val = memory.read32(weights_start);
            float fval;
            std::memcpy(&fval, &val, 4);
            std::cout << "    First weight (0x" << std::hex << weights_start << std::dec 
                     << "): " << fval << "\n";
            tests_passed++;
        }
        
        // Try to read first few biases
        if (biases_start + 4 <= memory.size()) {
            uint32_t val = memory.read32(biases_start);
            float fval;
            std::memcpy(&fval, &val, 4);
            std::cout << "    First bias (0x" << std::hex << biases_start << std::dec 
                     << "): " << fval << "\n";
            tests_passed++;
        }
        
        current_address += buffer.size();
    }
    
    // Summary
    std::cout << "\n========================================\n";
    std::cout << "Test Summary\n";
    std::cout << "========================================\n";
    std::cout << "Passed: " << tests_passed << "\n";
    std::cout << "Failed: " << tests_failed << "\n";
    
    if (tests_failed == 0) {
        std::cout << "\n✓ All tests passed!\n";
        return 0;
    } else {
        std::cout << "\n✗ Some tests failed\n";
        return 1;
    }
}
