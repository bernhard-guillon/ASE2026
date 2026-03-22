# PHASE 2: Neural Network Code Generation & Execution

## Status: Phase 1 Complete ✅ | Phase 2 Starting 🚀

### Latest Stats
- **Test Suite:** 307/307 passing (100%)
- **Target:** Execute trained neural network model on emulator
- **Architecture:** Memory-efficient cyclic inference loop

---

## Sprint 1: Design & Analysis (Current)

### 1.1 Memory Layout Design
- [ ] Visualize memory regions (code, weights, buffers, output)
- [ ] Calculate space requirements per network size
- [ ] Document allocation strategy
- [ ] Create memory map diagram

### 1.2 Model Format Analysis
- [ ] Load and analyze trained model (JSON)
- [ ] Understand weight tensor layout
- [ ] Identify layer types and configurations
- [ ] Plan code generation strategy

### 1.3 Execution Strategy
- [ ] Design cyclic layer-by-layer computation
- [ ] Plan register allocation
- [ ] Document data flow
- [ ] Identify optimization opportunities

---

## Sprint 2: Code Generation Engine (Coming)

### 2.1 Model Loader
- [ ] Parse trained model JSON
- [ ] Extract layer definitions
- [ ] Load weight tensors
- [ ] Validate structure

### 2.2 Assembly Generator
- [ ] Dense layer template
- [ ] Weight multiplication code
- [ ] Bias addition code
- [ ] Activation function insertion

### 2.3 Code Generation Pipeline
- [ ] Model → Intermediate representation
- [ ] IR → Assembly snippets
- [ ] Snippets → Linked program
- [ ] Test on simple models

### 2.4 Memory Allocator
- [ ] Calculate total space needed
- [ ] Assign regions for weights/buffers
- [ ] Generate layout assembly code
- [ ] Support variable network sizes

---

## Sprint 3: Execution Framework (Coming)

### 3.1 Cyclic Execution Loop
- [ ] Input reading mechanism
- [ ] Layer computation sequencing
- [ ] Output writing to framebuffer
- [ ] Loop control

### 3.2 Input/Output Handling
- [ ] Map input register to network input
- [ ] Map network output to framebuffer
- [ ] Support different I/O sizes
- [ ] Error handling

### 3.3 Framebuffer Integration
- [ ] Display network results
- [ ] Character-based visualization
- [ ] Support multiple output sizes
- [ ] Visual verification tools

---

## Sprint 4: Testing & Validation (Coming)

### 4.1 Unit Tests
- [ ] Code generator tests
- [ ] Weight loading verification
- [ ] Memory calculation validation
- [ ] Assembly syntax checking

### 4.2 Integration Tests
- [ ] End-to-end compilation
- [ ] Load and execute generated code
- [ ] Verify numerical correctness
- [ ] Compare with reference implementation

### 4.3 Performance & Optimization
- [ ] Execution time measurement
- [ ] Bottleneck identification
- [ ] Performance optimization
- [ ] Benchmark suite

---

## How to Continue

### Start Phase 2:
```bash
cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator

# Sprint 1: Design Phase
# 1. Examine trained model format
# 2. Design memory layout
# 3. Plan code generation approach
```

### Build & Test:
```bash
rm -rf build && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
ctest -j4    # Verify: 307/307 tests passing
```

---

## Key Decisions (Phase 1 → Phase 2)

✅ Hard-float ABI for FP operations  
✅ ReLU via FMAX.S instruction  
✅ Sigmoid via piecewise linear (no exp)  
✅ Pure RISC-V assembly generation  
✅ Character framebuffer visualization  
✅ Cyclic execution model  

---

## Success Criteria

- [ ] Load trained model from JSON
- [ ] Generate RISC-V assembly from model
- [ ] Execute on emulator successfully
- [ ] Display results in framebuffer
- [ ] Run cyclic inference loop
- [ ] All tests passing
- [ ] Reasonable execution time

---

**Phase 1:** 307/307 tests ✅ Hard-float ABI ✅ Activation functions ✅  
**Phase 2:** Starting now 🎯
