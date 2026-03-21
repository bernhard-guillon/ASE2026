# NEURAL_FC Custom Instruction - AI Extension for RISC-V Emulator

## Overview

NEURAL_FC is a custom RISC-V instruction designed to execute fully-connected neural network layers with built-in activation functions. This instruction enables efficient inference of neural networks directly on the emulator with precise timing characteristics.

## Vision

Add AI inference capability to the RISC-V emulator by:
- Implementing one custom instruction per neural network layer
- Pre-loading model weights in emulator memory
- Enabling real-time profiling of layer execution times
- Supporting character generation/recognition workflows
- Demonstrating custom ISA extensions for AI workloads

## Architecture

### Instruction Format

```
NEURAL_FC: Custom opcode 0x77 (proposed)
Field: [opcode(7) | reserved(25)]
```

Register-based parameter passing (following RISC-V calling convention):
- **a0 (x10)**: Input vector memory address
- **a1 (x11)**: Output vector memory address  
- **a2 (x12)**: Weights and biases memory address
- **a3 (x13)**: Input size (number of input neurons)
- **a4 (x14)**: Output size (number of output neurons)
- **a5 (x15)**: Activation type
  - 0 = NONE (linear)
  - 1 = RELU
  - 2 = SIGMOID

### Activation Functions

#### RELU (Rectified Linear Unit)
```c
output = max(0, sum)
```
Used for hidden layers to introduce non-linearity.

#### SIGMOID
```c
output = 1.0 / (1.0 + exp(-sum))
```
Used for output normalization (e.g., pixel values in [0,1]).

#### NONE (Linear)
```c
output = sum
```
Direct output of accumulated value.

## Execution

### Algorithm

For each output neuron i (0 to output_size-1):
1. Load bias: `bias[i]` from weights memory
2. Compute sum = bias[i]
3. For each input neuron j (0 to input_size-1):
   - Load input: `input[j]` from input vector
   - Load weight: `weight[i][j]` from weights memory
   - Accumulate: `sum += input[j] * weight[i][j]`
4. Apply activation: `output[i] = activation(sum)`
5. Store result: Write `output[i]` to output vector

### Computational Complexity

Time complexity: O(input_size × output_size)

For a fully-connected layer:
- Matrix multiplication: input_size × output_size operations
- Activation function: output_size operations
- Total FLOPs: ~input_size × output_size + output_size

### Memory Layout

Weights are stored contiguously in memory:
```
weights_address + 0:              weight[0][0] (first weight)
...
weights_address + (input_size × output_size × 4) - 4:  weight[output_size-1][input_size-1]

weights_address + (input_size × output_size × 4):      bias[0]
...
weights_address + (input_size × output_size × 4) + (output_size × 4) - 4: bias[output_size-1]
```

All values stored as IEEE 754 single-precision floats (4 bytes each).

## Memory Requirements

### Character Generator Model
```
Layer 0: 255 inputs × 256 outputs
  Weights: 255 × 256 × 4 = 261,120 bytes
  Biases: 256 × 4 = 1,024 bytes
  Total: 262,144 bytes

Layer 1: 256 inputs × 256 outputs
  Weights: 256 × 256 × 4 = 262,144 bytes
  Biases: 256 × 4 = 1,024 bytes
  Total: 263,168 bytes

Layer 2: 256 inputs × 400 outputs
  Weights: 256 × 400 × 4 = 409,600 bytes
  Biases: 400 × 4 = 1,600 bytes
  Total: 411,200 bytes

Total for generator: ~936 KB
```

### Character Recognition Model
```
Layer 0: 400 inputs × 128 outputs
  Weights: 400 × 128 × 4 = 204,800 bytes
  Biases: 128 × 4 = 512 bytes
  Total: 205,312 bytes

Layer 1: 128 inputs × 37 outputs
  Weights: 128 × 37 × 4 = 18,944 bytes
  Biases: 37 × 4 = 148 bytes
  Total: 19,092 bytes

Total for recognizer: ~225 KB
```

## Execution Timing

Approximate cycle counts (at implementation stage):

### Character Generator
```
Layer 0 (255→256): ~51,200 cycles
Layer 1 (256→256): ~65,536 cycles
Layer 2 (256→400): ~102,400 cycles
Total: ~219,136 cycles

@ 100 MHz: ~2.2 ms
@ 1 GHz: ~0.22 ms
```

### Character Recognition
```
Layer 0 (400→128): ~51,200 cycles
Layer 1 (128→37): ~4,736 cycles
Total: ~55,936 cycles

@ 100 MHz: ~0.56 ms
@ 1 GHz: ~0.056 ms
```

These timings enable:
- Profiling individual layers
- Identifying bottlenecks
- Planning hardware optimizations
- Understanding real-time constraints

## Assembly Usage

### Basic Template
```asm
# Execute fully-connected layer
la a0, input_vector      # Input address
la a1, output_vector     # Output address
la a2, weights_data      # Weights and biases
li a3, 255               # Input size
li a4, 256               # Output size
li a5, 1                 # Activation: RELU
neural_fc                # Execute layer

# Next instruction executes automatically
```

### Complete Example: Character Generation

```asm
.section .data
  # Input vectors
  input_vector:    .space 255*4    # 255 floats for input
  hidden_vec1:     .space 256*4    # 256 hidden outputs
  hidden_vec2:     .space 256*4    # 256 hidden outputs
  output_glyph:    .space 400*4    # 400 pixel values
  
  # Weights (loaded from file at startup)
  weights_fc0:     .space 261120   # 255*256*4 + 256*4
  weights_fc1:     .space 262144   # 256*256*4 + 256*4
  weights_fc2:     .space 409600   # 256*400*4 + 400*4

.section .text
.global main

main:
    # Layer 0: 255→256 with ReLU
    la a0, input_vector
    la a1, hidden_vec1
    la a2, weights_fc0
    li a3, 255
    li a4, 256
    li a5, 1              # RELU
    neural_fc
    
    # Layer 1: 256→256 with ReLU
    la a0, hidden_vec1
    la a1, hidden_vec2
    la a2, weights_fc1
    li a3, 256
    li a4, 256
    li a5, 1              # RELU
    neural_fc
    
    # Layer 2: 256→400 with Sigmoid
    la a0, hidden_vec2
    la a1, output_glyph
    la a2, weights_fc2
    li a3, 256
    li a4, 400
    li a5, 2              # SIGMOID
    neural_fc
    
    # Write result to framebuffer
    li a7, 999            # Framebuffer syscall
    ecall
    
    # Exit
    li a7, 93
    li a0, 0
    ecall
```

## Implementation Phases

### Phase 1: Weight Export (Python)
- Extract model weights from trained PyTorch models
- Save to binary format with metadata
- Files: `character_generator_weights.bin`, `character_recognition_weights.bin`
- Duration: 1-2 hours

### Phase 2: Custom Opcode (C++)
- Add NEURAL_FC instruction decoder
- Implement fully-connected computation
- Add activation functions
- Register custom opcode in CPU
- Duration: 3-4 hours

### Phase 3: Testing & Validation
- Load weights into emulator memory
- Execute sample inference
- Compare outputs with Python reference
- Validate correctness
- Duration: 1-2 hours

### Phase 4: Framebuffer Integration
- Add framebuffer syscall (opcode 999)
- Visualize output glyphs
- Create end-to-end demonstration
- Duration: 2-3 hours

### Phase 5: Optimizations (Optional, Future)
- SIMD variants (process multiple neurons per instruction)
- Quantization support (int8/fp16)
- Caching strategies
- Hardware profiling enhancements
- Duration: 4+ hours

## Extensions & Future Work

### SIMD Variants
```
NEURAL_FC_SIMD4: Process 4 neurons in parallel
NEURAL_FC_SIMD8: Process 8 neurons in parallel
```

### Quantization
```
Support for reduced precision:
- INT8 (8-bit integer weights)
- FP16 (half-precision floats)
- INT4 (4-bit quantization)
```

### Advanced Layers
```
NEURAL_CONV2D: 2D Convolution
NEURAL_POOL: Max/Average Pooling
NEURAL_LSTM: LSTM cell
NEURAL_SOFTMAX: Softmax normalization
```

### Hardware Profiling
```
Track per-layer:
- Execution cycles
- Cache misses
- Memory bandwidth
- Power consumption
```

## Testing Strategy

### Correctness Validation
1. Export weights from trained PyTorch models
2. Load into emulator memory
3. Run NEURAL_FC instruction with test inputs
4. Compare outputs with PyTorch reference
5. Verify activation functions work correctly

### Performance Benchmarking
1. Measure cycles per layer
2. Profile memory access patterns
3. Calculate throughput (FLOPs/cycle)
4. Compare with theoretical peak

### Integration Testing
1. Test character generation pipeline
2. Test character recognition pipeline
3. End-to-end inference validation
4. Framebuffer visualization

## References

- RISC-V Instruction Set Manual
- PyTorch Model Export
- IEEE 754 Floating-Point Standard
- Neural Network Optimization Techniques

## Status

- [x] Architecture Design
- [x] Specification Documentation
- [ ] Phase 1: Weight Export
- [ ] Phase 2: Opcode Implementation
- [ ] Phase 3: Testing
- [ ] Phase 4: Framebuffer Integration
- [ ] Phase 5: Optimizations

## Next Steps

Begin Phase 1 implementation: Extract and export model weights to binary format.
