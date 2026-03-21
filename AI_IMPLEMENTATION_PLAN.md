# AI Model Integration with NEURAL_FC - Implementation Plan

## Project Vision

Add neural network inference capability to the RISC-V emulator through custom instructions, enabling:
- Real-time AI inference directly on the emulator
- Precise timing/profiling of neural network layers
- Character generation (ASCII → 20×20 pixel glyph)
- Character recognition (20×20 pixel image → 37 classes)
- Foundation for AI-specific ISA extensions

## Models

### Character Generator
- **Purpose:** Convert ASCII character code to pixel glyph
- **Input:** 255-dimensional one-hot vector (ASCII encoding)
- **Output:** 400 pixel values (20×20 image)
- **Architecture:**
  - Layer 0: FC(255→256) + ReLU
  - Layer 1: FC(256→256) + ReLU
  - Layer 2: FC(256→400) + Sigmoid
- **Model Size:** ~120 KB

### Character Recognition
- **Purpose:** Recognize character from pixel image
- **Input:** 400 pixel values (20×20 image)
- **Output:** 37 class scores (A-Z, 0-9, space, period)
- **Architecture:**
  - Layer 0: FC(400→128) + ReLU
  - Layer 1: FC(128→37) (logits)
- **Model Size:** ~20 KB

## Implementation Timeline

### Phase 1: Weight Export (1-2 hours)
**Goal:** Extract model weights and prepare for emulator loading

**Tasks:**
1. Create weight export utility in Python
2. Export character-generation model weights
3. Export character-recognition model weights
4. Create metadata files with layer information
5. Validate exported weights format
6. Test loading weights back into models

**Deliverables:**
- `export_weights.py` - Python utility
- `character_generator_weights.bin` - Binary weight file
- `character_recognition_weights.bin` - Binary weight file
- `model_metadata.json` - Layer descriptions

**Files to modify:**
- `projects/character-generation/src/train.py` - Add export code
- `projects/character-recognition/src/train.py` - Add export code

**Verification:**
- Weights load successfully
- File sizes reasonable (~120 KB + ~20 KB)
- Binary format matches specification

---

### Phase 2: Emulator Extensions (3-4 hours)
**Goal:** Add NEURAL_FC custom instruction to CPU/emulator

**Tasks:**
1. Define custom opcode (0x77 for NEURAL_FC)
2. Add instruction decoder in CPU
3. Implement fully-connected computation
4. Implement ReLU activation
5. Implement Sigmoid activation
6. Add register parameter extraction
7. Implement memory access for weights/vectors
8. Update PC after instruction completion
9. Add cycle counting for profiling

**Deliverables:**
- Modified `CPU.h` - Add instruction handling
- Modified `CPU.cpp` - Implement NEURAL_FC execution
- Opcode definition and documentation
- Cycle counting mechanism

**Files to modify:**
- `projects/emulator/CPU.h` - Add method declaration
- `projects/emulator/CPU.cpp` - Add NEURAL_FC implementation
- `projects/emulator/Instruction.h` - Add opcode definition

**Code Structure:**
```cpp
// In CPU.cpp
void CPU::executeNeuralFC(const Instruction& instr) {
    // Extract parameters from registers
    // Read input vector from memory
    // Read weights and biases from memory
    // Perform fully-connected computation
    // Apply activation function
    // Write output vector to memory
    // Update performance counters
    incrementPC();
}
```

**Verification:**
- Instruction decodes correctly
- Parameters extracted properly
- Computation matches reference implementation
- Cycle counts reasonable

---

### Phase 3: Model Loading & Testing (1-2 hours)
**Goal:** Load weights into emulator and validate correctness

**Tasks:**
1. Add model loading function to Emulator
2. Load weights into reserved memory region
3. Create test programs in assembly
4. Test character generation inference
5. Test character recognition inference
6. Validate outputs match Python reference
7. Measure execution times per layer
8. Document timing results

**Deliverables:**
- `emulator_load_weights.cpp` - Weight loading code
- Assembly test programs
- Output validation tests
- Timing/profiling results

**Files to modify:**
- `projects/emulator/Emulator.h` - Add weight loading
- `projects/emulator/Emulator.cpp` - Implement loading
- `projects/emulator/CMakeLists.txt` - Add test programs

**Test Programs to Create:**
- `test_neural_fc_generation.s` - Generate glyph for character
- `test_neural_fc_recognition.s` - Recognize character from glyph
- Unit tests comparing with Python outputs

**Verification:**
- Outputs match Python reference (within float precision)
- Execution times profiled
- No memory errors or crashes
- All tests passing

---

### Phase 4: Framebuffer Integration (2-3 hours)
**Goal:** Add visualization capability and end-to-end demo

**Tasks:**
1. Add framebuffer memory region
2. Create framebuffer syscall (opcode 999)
3. Implement pixel write operations
4. Create visualization output (PPM/PNG format)
5. Build end-to-end demo program
6. Test character generation to framebuffer
7. Generate sample glyph images
8. Create documentation and examples

**Deliverables:**
- Framebuffer syscall implementation
- Demo assembly program
- Generated glyph images
- Visualization scripts

**Files to modify:**
- `projects/emulator/Emulator.cpp` - Add framebuffer syscall
- Create demo program assembly file
- Create image output utilities

**Framebuffer Memory Layout:**
```
Framebuffer address: 0xA0000
Resolution: 1024×768 pixels
Pixel format: 8-bit grayscale (0-255)
Total size: 786,432 bytes
```

**Verification:**
- Framebuffer writes work correctly
- Generated images visualize properly
- End-to-end demo runs successfully
- Performance acceptable

---

### Phase 5: Optional Optimizations (4+ hours, Future)
**Goal:** Add advanced features for better performance

**Tasks:**
1. Implement SIMD variants (process multiple neurons per cycle)
2. Add quantization support (INT8, FP16)
3. Implement caching strategies
4. Add detailed profiling output
5. Create optimization guidelines
6. Benchmark various configurations

**Not required for basic functionality - consider for Phase 2 of project**

---

## Memory Layout

```
0x00000000 - 0x00000FFF: Program Code (4 KB)
0x00001000 - 0x00007FFF: Heap/Stack (28 KB)
0x00008000 - 0x00008FFF: Input Buffers (4 KB)
  - input_vector[255] @ 0x8000
  - hidden_vec1[256] @ 0x8400
  - hidden_vec2[256] @ 0x8C00
0x00009000 - 0x0000EFFF: Output Buffers (24 KB)
  - output_glyph[400] @ 0x9000
  - framebuffer[786432] @ 0xA0000
0x00010000 - 0x003FFFFF: Model Weights (960 KB)
  - Generator weights (936 KB)
  - Recognition weights (225 KB)
```

## Testing Strategy

### Unit Tests
- [ ] NEURAL_FC with known inputs
- [ ] Activation functions (ReLU, Sigmoid)
- [ ] Memory access patterns
- [ ] Edge cases (zero inputs, large values)

### Integration Tests
- [ ] Load complete models
- [ ] Run full inference sequences
- [ ] Compare with Python outputs
- [ ] Verify all layers execute correctly

### Performance Tests
- [ ] Measure cycles per layer
- [ ] Profile memory bandwidth
- [ ] Calculate throughput
- [ ] Identify bottlenecks

### End-to-End Tests
- [ ] Character generation pipeline
- [ ] Character recognition pipeline
- [ ] Framebuffer visualization
- [ ] Complete demo execution

## Success Criteria

### Phase 1 Complete ✓
- [ ] Weights extracted from both models
- [ ] Binary format created and documented
- [ ] Files load successfully
- [ ] File sizes within expected range

### Phase 2 Complete ✓
- [ ] NEURAL_FC instruction decodes correctly
- [ ] All register parameters extracted
- [ ] Fully-connected computation correct
- [ ] Activation functions working
- [ ] Cycle counting functional

### Phase 3 Complete ✓
- [ ] Weights load into emulator memory
- [ ] Sample inference produces correct output
- [ ] Results match Python reference (within fp32 precision)
- [ ] Execution times profiled and reasonable

### Phase 4 Complete ✓
- [ ] Framebuffer syscall functional
- [ ] Glyphs render correctly
- [ ] End-to-end demo works
- [ ] Sample output images generated

## Risk Assessment

### Low Risk
- Weight export (standard PyTorch operations)
- Framebuffer syscall (simple memory writes)
- Testing framework (using existing test infrastructure)

### Medium Risk
- Floating-point precision differences (CPU vs PyTorch)
  - Mitigation: Allow small tolerance in comparisons
- Memory layout conflicts
  - Mitigation: Careful address planning
- Performance not meeting expectations
  - Mitigation: Profile early, optimize as needed

### High Risk (Addressed by design)
- Model complexity beyond FC layers
  - Addressed: Using simple models without custom operations
- Insufficient memory
  - Addressed: Pre-sized memory to 512+ MB for weights

## Documentation

### Code Documentation
- Inline comments explaining NEURAL_FC implementation
- Function documentation for all new methods
- Memory layout diagrams
- Timing analysis

### User Documentation
- Assembly programming guide for NEURAL_FC
- Model format specification
- Examples and tutorials
- API reference

### Technical Reports
- Timing/performance analysis
- Memory usage breakdown
- Comparison with Python inference
- Extension recommendations

## Deliverables Summary

### Code
- [ ] `export_weights.py` - Weight export utility
- [ ] Modified training scripts with export
- [ ] NEURAL_FC instruction implementation
- [ ] Weight loading functions
- [ ] Framebuffer syscall
- [ ] Test programs and utilities

### Documentation
- [ ] NEURAL_FC.md - Instruction specification
- [ ] Implementation plan (this file)
- [ ] API documentation
- [ ] Assembly programming guide
- [ ] Performance analysis report

### Data
- [ ] Binary weight files for both models
- [ ] Metadata files describing models
- [ ] Sample output images
- [ ] Timing/profiling data

### Tests
- [ ] Unit tests for computation
- [ ] Integration tests for pipeline
- [ ] Performance benchmarks
- [ ] End-to-end demo program

## Resources Required

### Personnel
- 1 developer (primary implementation)
- Optional: 1 reviewer/advisor

### Computing
- Existing development environment
- ~100 MB disk space for code + weights
- GPU optional (only for training)

### Tools
- PyTorch (already in use)
- C++ compiler (GCC/Clang)
- CMake build system
- Python 3.x

## Timeline Estimate

- **Phase 1:** 1-2 hours
- **Phase 2:** 3-4 hours  
- **Phase 3:** 1-2 hours
- **Phase 4:** 2-3 hours
- **Total:** ~10-12 hours over 1-2 weeks

## Next Steps

1. Proceed with Phase 1: Weight Export
2. Create Python export utility
3. Test weight extraction
4. Prepare for Phase 2 emulator modifications

## References

- NEURAL_FC.md - Instruction specification
- RISC-V ISA Manual - Instruction encoding
- PyTorch Documentation - Model export
- IEEE 754 Floating-Point Standard - Computation accuracy

## Status

**Created:** 2026-03-21  
**Phase:** Planning → Phase 1 (Weight Export)  
**Last Updated:** 2026-03-21

---

## Notes

This is an ambitious and interesting project that combines:
- Custom ISA design (NEURAL_FC instruction)
- Neural network implementation
- Real-time system characteristics
- Educational value

The phased approach allows for incremental validation and course correction.
