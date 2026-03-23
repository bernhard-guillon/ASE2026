# Phase 2 Sprint 1: Design & Analysis Complete

**Date:** 2026-03-22  
**Status:** ✅ Complete  
**Tests:** 307/307 passing (100%)  

## Overview

Sprint 1 of Phase 2 focused on designing the foundation for neural network code generation and execution on our RISC-V emulator. This sprint produced comprehensive documentation for memory layout, model architecture analysis, and execution strategy.

## Deliverables

### 1. Model Architecture Analysis

Analyzed both trained models in the project:

**Character Generator Model:**
- Architecture: 3 Dense layers
- Structure: [255 → 256 → 256 → 400]
- Activations: ReLU, ReLU, Sigmoid
- Weights: 233,216 floats (932,864 bytes)
- Biases: 912 floats (3,648 bytes)
- Total: 914.56 KB

**Character Recognizer Model:**
- Architecture: 2 Dense layers
- Structure: [400 → 128 → 37]
- Activations: ReLU, None (logits)
- Weights: 55,936 floats (223,744 bytes)
- Biases: 165 floats (660 bytes)
- Total: 219.14 KB

**Combined:** 1.11 MB total model data

### 2. Memory Layout Design

Designed complete RISC-V RV32IMF memory map:

```
0x00000000 - 0x00000FFF : NULL guard (4 KB)
0x00001000 - 0x0000FFFF : Code section (60 KB)
0x00010000 - 0x0010FFFF : Generator model (1 MB)
0x00110000 - 0x0014FFFF : Recognizer model (256 KB)
0x00150000 - 0x001FFFFF : Runtime buffers (704 KB)
0x00200000 - 0x003FFFFF : Framebuffer (2 MB)
0x00400000 - 0x7FFFFFFF : Heap (dynamic)
0x80000000 - 0xFFFFFFFF : Stack (grows down)
```

**Binary Format Specification:**
- Header: 32 bytes (magic, version, model_type, num_layers, etc.)
- Layer table: 32 bytes per layer (sizes, activation, offsets)
- Weight data: Row-major float32 arrays
- Bias data: Float32 arrays
- All data 4-byte aligned

### 3. Execution Strategy

**Forward Pass Algorithm:**
- Dense layer computation via matrix multiplication
- RISC-V assembly implementation using FMUL.S, FADD.S
- Activation functions: FMAX.S (ReLU), piecewise linear (Sigmoid)
- Double-buffered activations (ping-pong between layers)

**Cyclic Execution Loop:**
1. Read input (random for generator, framebuffer for recognizer)
2. Execute forward pass through all layers
3. Write output to framebuffer
4. Loop indefinitely

**Register Allocation:**
- s0-s5: Model state (preserved across calls)
- a0-a7: Function arguments
- fa0-fa7: Floating-point arguments
- t0-t6: Scratch temporaries

### 4. Performance Estimates

**Generator Model:**
- FP operations: 466,432 (233,216 FMUL + 233,216 FADD)
- Estimated cycles: ~5.4M (including memory access)
- Time @ 100MHz: ~54 μs per inference

**Recognizer Model:**
- FP operations: 111,872 (55,936 FMUL + 55,936 FADD)
- Estimated cycles: ~1.3M (including memory access)
- Time @ 100MHz: ~11 μs per inference

**Conclusion:** Real-time execution is feasible for interactive character generation and recognition.

## Key Technical Decisions

1. **Static Memory Allocation**
   - All models fit in <2 MB
   - No dynamic loading needed
   - Simplifies implementation and testing

2. **Row-Major Weight Storage**
   - Sequential memory access pattern
   - Cache-friendly (when cache exists)
   - Standard matrix library layout

3. **Double-Buffered Activations**
   - Ping-pong between input/output buffers
   - Avoids memory conflicts
   - Enables future pipelining optimizations

4. **Binary Format with Headers**
   - Self-describing model data
   - Version management support
   - Easy validation and debugging

5. **Pure Assembly Code Generation**
   - Full control over instruction sequences
   - Predictable performance
   - No compiler surprises or ABI issues

## Assembly Code Templates

### Dense Layer Forward Pass

```assembly
layer_forward_dense:
    # Arguments:
    #   a0 = input buffer
    #   a1 = weight matrix
    #   a2 = bias vector
    #   a3 = output buffer
    #   a4 = input_size
    #   a5 = output_size
    #   a6 = activation (0=relu, 1=sigmoid, 2=none)
    
    li s0, 0                    # output index j
.outer_loop:
    bge s0, a5, .done
    
    # Load bias[j]
    slli t0, s0, 2
    add t1, a2, t0
    flw fa0, 0(t1)              # accumulator = bias[j]
    
    li s1, 0                    # input index i
.inner_loop:
    bge s1, a4, .apply_activation
    
    # Load input[i]
    slli t0, s1, 2
    add t1, a0, t0
    flw fa1, 0(t1)
    
    # Load weight[i][j]
    mul t0, s1, a5
    add t0, t0, s0
    slli t0, t0, 2
    add t1, a1, t0
    flw fa2, 0(t1)
    
    # acc += input[i] * weight[i][j]
    fmul.s fa3, fa1, fa2
    fadd.s fa0, fa0, fa3
    
    addi s1, s1, 1
    j .inner_loop

.apply_activation:
    # Apply activation based on a6
    beq a6, zero, .relu
    li t0, 1
    beq a6, t0, .sigmoid
    j .store_output
    
.relu:
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1
    j .store_output
    
.sigmoid:
    call sigmoid_piecewise
    j .store_output

.store_output:
    slli t0, s0, 2
    add t1, a3, t0
    fsw fa0, 0(t1)
    
    addi s0, s0, 1
    j .outer_loop

.done:
    ret
```

## Documentation References

For detailed specifications, see session state files:
- `SPRINT1_DESIGN.md`: Complete technical specification (16 KB)
- `MEMORY_MAP.txt`: Visual memory layout diagram (14 KB)

## Test Status

- All 307 tests passing (100%)
- No code changes in Sprint 1 (design only)
- Ready for Sprint 2 implementation

## Next Steps: Sprint 2

**Code Generation Engine deliverables:**

1. **Model Loader**
   - Parse JSON intermediate format
   - Extract layer definitions and weights
   - Validate model structure

2. **Binary Format Generator**
   - Create binary headers
   - Package weights/biases as .bin files
   - Generate layer tables

3. **Assembly Code Generator**
   - Generate model data section
   - Generate layer computation routines
   - Generate execution loop
   - Link all components

4. **Test Infrastructure**
   - Unit tests for code generator
   - Numerical verification tests
   - Reference implementation comparison

## Dependencies

Sprint 2 builds on:
- ✅ Phase 1: Complete RISC-V F extension (all FP instructions)
- ✅ Phase 1: Hard-float ABI support (-mabi=ilp32f)
- ✅ Phase 1: ReLU and Sigmoid activation functions
- ✅ Phase 1: ELF loader for code execution
- ✅ Phase 1: Framebuffer rendering (character grid)

## Success Criteria

Sprint 1 achieved:
- ✅ Complete memory layout specification
- ✅ Model architecture documentation
- ✅ Execution strategy design
- ✅ Performance analysis
- ✅ Binary format specification
- ✅ Assembly code templates

---

**Sprint 1:** Complete ✅  
**Sprint 2:** Ready to start 🚀  
**Phase 2 Progress:** 25% (1/4 sprints)
