# Neural Network Execution Plan

**Status:** Planning  
**Date:** March 22, 2026  
**Goal:** Implement cyclic neural network execution with deterministic instruction flow

## Overview

This plan describes how to execute a loaded neural network model in a cyclic manner, where each layer computation is represented as a discrete instruction or code block, creating a predictable execution pattern.

## Design Decisions

### Input Mechanism
**Decision:** Use register-based input (same approach as static character generation)
- Reuse existing register input mechanism from static character generation
- Whatever value is in the designated register when entering the input phase becomes the network input
- Need to define a mapping from 32-bit register value to model input representation
- **Initial approach:** Use register value directly, refine mapping later

**Rationale:** 
- Maintains consistency with existing static character generation system
- Simplifies initial implementation
- Allows for iterative refinement of input representation

### Output Handling
**Decision:** Use framebuffer output (same as static character generation)
- Reuse existing framebuffer from static character generation
- Network output written to same framebuffer location
- Enables direct visual comparison between static and AI-generated output

**Rationale:**
- Consistency with existing system
- Enables validation testing (blackbox test comparing static vs AI on all possible inputs)
- Provides visual feedback for debugging

### Performance Goals
**Decision:** No hard performance target initially, focus on correctness
- Real-time constraints should be easily achievable
- Derive formula: `Time = f(layers, neurons, weights, instruction_cycles)`
- After baseline milestone: optimize instruction selection and memory usage
- Establish benchmark suite comparing static vs AI performance

**Rationale:**
- Get it working first, optimize second
- Predictable architecture enables performance modeling
- Allows data-driven optimization decisions

### Testing Strategy
**Decision:** Comprehensive blackbox comparison test
- Test all possible inputs (within character generation domain)
- Compare static character generation vs AI-based generation
- Validate correctness before optimization
- Establish performance baseline for future improvements

**Rationale:**
- Validates implementation correctness
- Provides regression testing for optimizations
- Quantifies any discrepancies between static and AI approaches

## Current State Analysis

### Memory Layout (Existing)

```
┌─────────────────────────────────────────────────────────┐
│ 0x00000000                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │           BOOTLOADER CODE (64 KB)                   │ │
│ │  - Stack initialization                             │ │
│ │  - Model loading loops                              │ │
│ │  - Verification code                                │ │
│ │  - Exit syscall                                     │ │
│ └─────────────────────────────────────────────────────┘ │
│ 0x00010000                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │           MODEL DATA SECTION (960 KB)               │ │
│ │                                                     │ │
│ │  Generator Model (0x10000 - 0xF3C7F)               │ │
│ │  ├── Header (32 bytes)                             │ │
│ │  ├── Layer Table (32 bytes × N layers)             │ │
│ │  ├── Weights for Layer 0                           │ │
│ │  ├── Biases for Layer 0                            │ │
│ │  ├── Weights for Layer 1                           │ │
│ │  ├── Biases for Layer 1                            │ │
│ │  └── ... (remaining layers)                        │ │
│ │                                                     │ │
│ │  Gap (0xF3C7F - 0xF4ABC)                           │ │
│ │                                                     │ │
│ │  Recognizer Model (0xF4ABC - 0xFFFFF)              │ │
│ │  └── (same structure as generator)                 │ │
│ └─────────────────────────────────────────────────────┘ │
│ 0x00100000                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │      APPLICATION MEMORY (reserved for future)       │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Model Binary Format (Existing)

```
Header (32 bytes):
  +0:  Magic number (0x4E52414E "NRAL")
  +4:  Version (1)
  +8:  Model type (0=generator, 1=recognizer)
  +12: Num layers
  +16: Total size (bytes)
  +20: Precision (32-bit float)
  +24-31: Reserved

Layer Table Entry (32 bytes × num_layers):
  +0:  Layer index
  +4:  Input size
  +8:  Output size
  +12: Activation function (0=relu, 1=sigmoid, 2=none)
  +16: Weights offset (from start of file)
  +20: Biases offset (from start of file)
  +24: Weights size (bytes)
  +28: Biases size (bytes)

Data Section:
  - Weights (float32 array, row-major: input_size × output_size)
  - Biases (float32 array: output_size)
```

## Proposed Execution Architecture

### 1. Extended Memory Map for Execution

```
┌──────────────────────────────────────────────────────────┐
│ 0x00000000                                               │
│ ┌────────────────────────────────────────────────────┐   │
│ │        BOOTLOADER CODE (64 KB)                     │   │
│ │  [EXISTING]                                        │   │
│ └────────────────────────────────────────────────────┘   │
│ 0x00010000                                               │
│ ┌────────────────────────────────────────────────────┐   │
│ │        MODEL DATA (Read-Only, 960 KB)              │   │
│ │  [EXISTING] - Weights and biases                   │   │
│ └────────────────────────────────────────────────────┘   │
│ 0x00100000                                               │
│ ┌────────────────────────────────────────────────────┐   │
│ │        EXECUTION CODE (NEW, 256 KB)                │   │
│ │                                                    │   │
│ │  Entry Point: 0x100000                            │   │
│ │  ├── Layer 0 Computation Code                     │   │
│ │  │   - Load input from input_buffer              │   │
│ │  │   - Matrix multiply with weights              │   │
│ │  │   - Add biases                                │   │
│ │  │   - Apply activation function                 │   │
│ │  │   - Store to layer0_output                    │   │
│ │  │   - Jump to Layer 1                           │   │
│ │  │                                               │   │
│ │  ├── Layer 1 Computation Code                     │   │
│ │  │   - Load input from layer0_output             │   │
│ │  │   - Matrix multiply with weights              │   │
│ │  │   - Add biases                                │   │
│ │  │   - Apply activation function                 │   │
│ │  │   - Store to layer1_output                    │   │
│ │  │   - Jump to Layer 2                           │   │
│ │  │                                               │   │
│ │  ├── Layer 2 Computation Code (hidden)            │   │
│ │  │   - Same pattern...                           │   │
│ │  │                                               │   │
│ │  ├── Layer N-1 Computation Code (output layer)    │   │
│ │  │   - Load input from layerN-2_output           │   │
│ │  │   - Matrix multiply with weights              │   │
│ │  │   - Add biases                                │   │
│ │  │   - Apply activation function                 │   │
│ │  │   - Store to output_buffer                    │   │
│ │  │   - Jump back to Entry Point (Layer 0)        │   │
│ │                                                    │   │
│ └────────────────────────────────────────────────────┘   │
│ 0x00140000                                               │
│ ┌────────────────────────────────────────────────────┐   │
│ │        WORKING MEMORY (NEW, 256 KB)                │   │
│ │                                                    │   │
│ │  Input Buffer:      0x140000 (max 1024 floats)   │   │
│ │  Layer 0 Output:    0x141000 (max 1024 floats)   │   │
│ │  Layer 1 Output:    0x142000 (max 1024 floats)   │   │
│ │  Layer 2 Output:    0x143000 (max 1024 floats)   │   │
│ │  ...                                              │   │
│ │  Output Buffer:     0x14F000 (max 1024 floats)   │   │
│ │  Temp/Scratch:      0x150000 (64 KB)             │   │
│ └────────────────────────────────────────────────────┘   │
│ 0x00180000                                               │
│ ┌────────────────────────────────────────────────────┐   │
│ │        STACK (256 KB)                              │   │
│ │  Stack Pointer: 0x1BFFFF (grows downward)         │   │
│ └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 2. Execution Flow (Cyclic)

```
Start
  ↓
┌─────────────────────────────────┐
│  PC = 0x100000 (Entry Point)    │ ← ┐
└──────────────┬──────────────────┘   │
               ↓                       │
┌─────────────────────────────────┐   │
│  Execute Layer 0 (Input Layer)  │   │
│  - Read from input_buffer       │   │
│  - Compute: output = W×input+b  │   │
│  - Apply activation (ReLU)      │   │
│  - Store to layer0_output       │   │
│  - PC += code_size              │   │
└──────────────┬──────────────────┘   │
               ↓                       │
┌─────────────────────────────────┐   │
│  Execute Layer 1 (Hidden)       │   │
│  - Read from layer0_output      │   │
│  - Compute: output = W×input+b  │   │
│  - Apply activation (ReLU)      │   │
│  - Store to layer1_output       │   │
│  - PC += code_size              │   │
└──────────────┬──────────────────┘   │
               ↓                       │
┌─────────────────────────────────┐   │
│  Execute Layer 2 (Hidden)       │   │
│  - Read from layer1_output      │   │
│  - Compute: output = W×input+b  │   │
│  - Apply activation (ReLU)      │   │
│  - Store to layer2_output       │   │
│  - PC += code_size              │   │
└──────────────┬──────────────────┘   │
               ↓                       │
┌─────────────────────────────────┐   │
│  Execute Layer N (Output)       │   │
│  - Read from layerN-1_output    │   │
│  - Compute: output = W×input+b  │   │
│  - Apply activation (Sigmoid)   │   │
│  - Store to output_buffer       │   │
│  - Jump to 0x100000 (restart)   │   │
└──────────────┬──────────────────┘   │
               └─────────────────────┘
               (Infinite Loop)
```

### 3. Layer Computation Code Template

Each layer gets its own code block with this pattern:

```assembly
# Layer N Computation
# Inputs:
#   a0 = input_address (from previous layer or input_buffer)
#   a1 = output_address (to current layer output)
#   a2 = weights_address (from model data)
#   a3 = biases_address (from model data)
#   a4 = input_size
#   a5 = output_size

layer_N_entry:
    # Save registers
    addi sp, sp, -64
    sw ra, 60(sp)
    sw s0-s11, 0(sp)
    
    # Setup pointers
    mv s0, a0          # input pointer
    mv s1, a1          # output pointer
    mv s2, a2          # weights pointer
    mv s3, a3          # biases pointer
    mv s4, a4          # input_size
    mv s5, a5          # output_size
    
    # Outer loop: for each output neuron
    li t0, 0           # output_idx
.outer_loop:
    bge t0, s5, .outer_done
    
    # Initialize accumulator with bias
    slli t1, t0, 2     # bias_offset = output_idx * 4
    add t2, s3, t1     # bias_address
    flw f0, 0(t2)      # accumulator = bias[output_idx]
    
    # Inner loop: for each input
    li t3, 0           # input_idx
.inner_loop:
    bge t3, s4, .inner_done
    
    # Load input value
    slli t4, t3, 2     # input_offset = input_idx * 4
    add t5, s0, t4
    flw f1, 0(t5)      # input_val = input[input_idx]
    
    # Load weight: W[output_idx][input_idx]
    # weight_offset = (output_idx * input_size + input_idx) * 4
    mul t6, t0, s4     # output_idx * input_size
    add t6, t6, t3     # + input_idx
    slli t6, t6, 2     # * 4 (float size)
    add t6, s2, t6     # + weights_base
    flw f2, 0(t6)      # weight_val
    
    # Multiply and accumulate
    fmul.s f3, f1, f2  # input * weight
    fadd.s f0, f0, f3  # accumulator += input * weight
    
    addi t3, t3, 1     # input_idx++
    j .inner_loop
    
.inner_done:
    # Apply activation function (ReLU in this example)
    fmv.s f1, f0       # copy accumulator
    li t1, 0
    fcvt.s.w f2, t1    # f2 = 0.0
    fmax.s f0, f0, f2  # ReLU: max(x, 0)
    
    # Store output
    slli t1, t0, 2     # output_offset = output_idx * 4
    add t2, s1, t1
    fsw f0, 0(t2)      # output[output_idx] = result
    
    addi t0, t0, 1     # output_idx++
    j .outer_loop
    
.outer_done:
    # Restore registers
    lw s0-s11, 0(sp)
    lw ra, 60(sp)
    addi sp, sp, 64
    
    # Jump to next layer (or loop back to start)
    j layer_N+1_entry
```

## Required Instructions Analysis

### Current RV32I Instructions (Implemented)
✅ **Integer ALU:**
- ADD, SUB, AND, OR, XOR, SLT, SLTU
- ADDI, ANDI, ORI, XORI, SLTI, SLTIU
- SLL, SRL, SRA, SLLI, SRLI, SRAI

✅ **Memory Access:**
- LW, LH, LB, LBU, LHU
- SW, SH, SB

✅ **Control Flow:**
- BEQ, BNE, BLT, BGE, BLTU, BGEU
- JAL, JALR

✅ **Upper Immediates:**
- LUI, AUIPC

✅ **System:**
- ECALL

### Required NEW Instructions (F Extension - Single Precision Float)

❌ **Floating Point Load/Store:** (Critical - Priority 1)
- `FLW rd, offset(rs1)` - Load float from memory
- `FSW rs2, offset(rs1)` - Store float to memory

❌ **Floating Point Arithmetic:** (Critical - Priority 1)
- `FADD.S rd, rs1, rs2` - Add floats
- `FSUB.S rd, rs1, rs2` - Subtract floats
- `FMUL.S rd, rs1, rs2` - Multiply floats (for matrix operations)
- `FDIV.S rd, rs1, rs2` - Divide floats (optional, can use approximation)

❌ **Floating Point Comparison:** (High Priority - Priority 2)
- `FLT.S rd, rs1, rs2` - Float less than (for activation functions)
- `FLE.S rd, rs1, rs2` - Float less or equal
- `FEQ.S rd, rs1, rs2` - Float equal
- `FMAX.S rd, rs1, rs2` - Float max (useful for ReLU)
- `FMIN.S rd, rs1, rs2` - Float min

❌ **Floating Point Conversion:** (Medium Priority - Priority 3)
- `FCVT.S.W rd, rs1` - Convert int32 to float
- `FCVT.W.S rd, rs1` - Convert float to int32

❌ **Floating Point Move/Sign:** (Low Priority - Priority 4)
- `FMV.S rd, rs1` - Move float register to float register
- `FMV.X.W rd, rs1` - Move float register to integer register
- `FMV.W.X rd, rs1` - Move integer register to float register
- `FSGNJ.S rd, rs1, rs2` - Float sign inject
- `FSGNJN.S rd, rs1, rs2` - Float sign inject negate
- `FSGNJX.S rd, rs1, rs2` - Float sign inject xor

### Register File Extension Needed

Current: 32 integer registers (x0-x31)
**NEW:** 32 floating point registers (f0-f31)

- Separate register file for FP operations
- Each FP register holds 32-bit IEEE 754 single precision float

## Implementation Phases

### Phase 1: F Extension Core (Weeks 1-2)
**Goal:** Implement minimal FP support for neural network execution

**Tasks:**
1. Add FP register file (32 × 32-bit registers) to CPU.h/cpp
2. Implement FLW/FSW instructions (FP load/store)
3. Implement FADD.S, FSUB.S, FMUL.S (core arithmetic)
4. Implement FMAX.S (for ReLU activation)
5. Implement FMV.S (register moves)
6. Add unit tests for each instruction

**Success Criteria:**
- All FP instructions decode correctly
- FP register file accessible via getFPReg/setFPReg
- Unit tests pass for FP arithmetic
- Can multiply two floats and store result

### Phase 2: Neural Network Execution Code Generator (Week 3)
**Goal:** Generate layer computation code from model

**Tasks:**
1. Extend model_compiler.py to generate execution code
2. Add layer code template generator
3. Calculate memory addresses for layer outputs
4. Generate jump instructions between layers
5. Create cyclic loop (output → input)

**New Compiler Outputs:**
- `model_exec.s` - Assembly code with layer computations
- Memory map with execution code and working buffers

**Success Criteria:**
- Can generate execution code from model JSON
- Each layer has dedicated code block
- Cyclic execution loop works

### Phase 3: Integration & Testing (Week 4)
**Goal:** End-to-end neural network execution

**Tasks:**
1. Integrate bootloader + execution code
2. Load model to 0x10000, execution code to 0x100000
3. Initialize input buffer with test data
4. Run cyclic execution and capture outputs
5. Verify outputs match Python reference implementation

**Success Criteria:**
- Model loads and executes in emulator
- Cyclic execution loops correctly
- Output matches expected values (within float tolerance)
- Predictable cycle count per inference

### Phase 4: Optimization & Extensions (Week 5+)
**Goal:** Performance and feature improvements

**Tasks:**
1. Implement remaining F extension instructions (FDIV, FSQRT, etc.)
2. Add activation function library (Sigmoid, Tanh, Softmax)
3. Optimize matrix multiplication (loop unrolling, SIMD if possible)
4. Add cycle counting for performance profiling
5. Document instruction timing for each layer

## Testing Strategy

### Unit Tests (Phase 1)
```cpp
TEST(FloatInstructionTest, FLW_LoadsFloat) {
    emulator.getMemory().write32(0x1000, 0x40490FDB); // π ≈ 3.14159
    // FLW f1, 0x1000(x0)
    emulator.executeInstruction(0x00000107); // Encoded FLW
    EXPECT_FLOAT_EQ(emulator.getFPReg(1), 3.14159f);
}

TEST(FloatInstructionTest, FADD_AddsFloats) {
    emulator.setFPReg(1, 2.5f);
    emulator.setFPReg(2, 3.5f);
    // FADD.S f3, f1, f2
    emulator.executeInstruction(0x002081D3); // Encoded FADD
    EXPECT_FLOAT_EQ(emulator.getFPReg(3), 6.0f);
}

TEST(FloatInstructionTest, FMUL_MultipliesFloats) {
    emulator.setFPReg(1, 2.0f);
    emulator.setFPReg(2, 3.5f);
    // FMUL.S f3, f1, f2
    emulator.executeInstruction(0x102081D3); // Encoded FMUL
    EXPECT_FLOAT_EQ(emulator.getFPReg(3), 7.0f);
}
```

### Integration Tests (Phase 3)
```python
def test_single_layer_inference():
    """Test a simple 1-layer network: y = W*x + b"""
    model = {
        "metadata": {"model_type": "test", "precision": "float32"},
        "layers": [{
            "index": 0,
            "input_size": 2,
            "output_size": 1,
            "weights": [[0.5, 1.0]],  # W = [0.5, 1.0]
            "biases": [0.25],         # b = 0.25
            "activation": "none"
        }]
    }
    
    # Compile model with execution code
    compiler.compile_with_execution(model, "test_model.s")
    
    # Assemble and load
    run_assembler("test_model.s", "test_model.bin")
    emulator.load_binary("test_model.bin")
    
    # Set input: x = [1.0, 2.0]
    emulator.write_float(INPUT_BUFFER, 1.0)
    emulator.write_float(INPUT_BUFFER + 4, 2.0)
    
    # Run one cycle (entry to output layer)
    emulator.run_until_address(OUTPUT_COMPLETE_ADDR)
    
    # Check output: y = 0.5*1.0 + 1.0*2.0 + 0.25 = 2.75
    output = emulator.read_float(OUTPUT_BUFFER)
    assert abs(output - 2.75) < 1e-6
```

## Success Metrics

**Phase 1 Complete:**
- ✅ 32 FP registers implemented
- ✅ 10+ FP instructions working
- ✅ 50+ unit tests passing
- ✅ Float arithmetic verified

**Phase 2 Complete:**
- ✅ Code generator produces valid assembly
- ✅ Layer code matches template
- ✅ Memory layout correct
- ✅ Cyclic loop generated

**Phase 3 Complete:**
- ✅ End-to-end inference works
- ✅ Outputs match Python reference
- ✅ Cyclic execution stable
- ✅ No memory corruption

**Phase 4 Complete:**
- ✅ Full F extension implemented
- ✅ Activation functions working
- ✅ Performance benchmarks documented
- ✅ Production-ready code

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| F extension complexity | HIGH | Start with minimal subset (FLW, FSW, FADD, FMUL) |
| Floating point precision | MEDIUM | Use IEEE 754, test against reference |
| Memory constraints | MEDIUM | Pre-calculate buffer sizes, validate fits in 1MB |
| Cycle count unpredictable | LOW | Use fixed-size code blocks, no dynamic branches |
| Debugging difficulty | HIGH | Add verbose logging, cycle-by-cycle tracing |

## Open Questions

1. **Input mechanism:** How do we feed new input to the network?
   - Option A: Syscall to read from stdin
   - Option B: Memory-mapped I/O buffer
   - Option C: Pre-load inputs at known address

2. **Output handling:** What do we do with network output?
   - Option A: Write to stdout via syscall
   - Option B: Store in memory and signal completion
   - Option C: Trigger interrupt/exception

3. **Multi-model support:** Can we run generator + recognizer in same cycle?
   - Probably need separate execution regions
   - Or sequential execution (generator → recognizer)

4. **Performance goals:** What's acceptable cycle count?
   - Need to benchmark against Python implementation
   - Target: <10M cycles per inference?

## Next Steps

1. **Review & approval of this plan**
2. **Create Phase 1 detailed task breakdown**
3. **Set up F extension branch**
4. **Begin FP register file implementation**
5. **Write first FP instruction unit test**

## References

- RISC-V F Extension Spec: https://riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf (Chapter 11)
- IEEE 754 Floating Point Standard
- Current bootloader documentation: `docs/guides/BOOTLOADER_IMPLEMENTATION.md`
