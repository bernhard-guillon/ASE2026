# ASE 2026 — Neural-driven Computing
Bernhard Guillon

## Introduction
Modern large language models and AI toolchains typically run inside heavy software stacks (OS + browser + runtime). Many applications will increasingly embed neural components at many layers of the stack. This project explores whether we can design a far more lightweight computing environment that can directly host perceptron-based neural models as first-class computational elements.

We propose to define a minimal instruction set (ISA) with a small set of neural/tensor primitives, implement an emulator for that ISA, and run small trained networks directly in the emulator. The effort covers ISA design, assembler/loader, model-to-ROM/memory serialization, and verification tooling (including automated black‑box tests).

## Vision
Create a compact, demonstrable platform where:
- A tiny neural model (e.g., a perceptron or small MLP) can be loaded and executed by a minimal runtime / emulator.
- The ISA is RISC-like (RISC-V inspired) and extended with a few neural-tensor primitives (matmul, activation, tensor ops).
- I/O is minimal: character input (keyboard-like device) and a simple framebuffer output. The pipeline is:
  Keyboard input → neural model inference → Framebuffer pixel output

The initial demonstration task: train a model that receives short character input and produces a corresponding framebuffer output (e.g., render text or glyphs). The emulator should be capable of loading the model into memory and running inference using the extended ISA.

## Technical approach

### ISA & Instruction set
- Base: use a small, RISC-like ISA (consider a subset of RISC-V for familiarity) and add a small set of neural primitives:
  - MATMUL (matrix multiply)
  - VECTOR_ADD, VECTOR_MUL, SCALAR_MUL
  - ACTIVATION (ReLU, sigmoid, tanh) or specific activation opcodes
  - LOAD_TENSOR / STORE_TENSOR (memory/register tensor movement)
  - SIMPLE_CONV (optional stretch goal)
- Define binary encodings and a minimal assembly syntax.
- Define register and memory model for tensor computations (e.g., vector registers, memory layout for tensors).

### Emulator
- Implement a cycle-accurate or instruction-accurate emulator (initially instruction-accurate).
- Provide:
  - CPU core with the chosen ISA and neural op implementations
  - Memory map and loader interface
  - Basic devices:
    - Character input device (read-only buffer / device register)
    - Framebuffer device (memory-mapped; simple pixel buffer)
    - Simple console for diagnostics
- The emulator will expose a simple boot/loader sequence to load program + model into memory and start execution.

### Model training & serialization
- Train small models in PyTorch (or a minimal trainer written as needed) for the demonstration tasks.
- Export trained model parameters in a compact format suitable for the emulator:
  - Options: ONNX → custom transpiler, or direct PyTorch export → custom converter
  - Consider quantization (e.g., 8-bit or 16-bit) to reduce memory footprint and simplify inference
- Define how model parameters are laid out in emulator memory and what the bootloader must do to place them correctly.

### Bootloader / Loader / Assembler / Transpiler
- Assemble demo programs for the ISA with a small assembler.
- Implement a loader (bootloader) that:
  - Places the program and model weights into memory
  - Initializes device registers (framebuffer pointer, input buffer pointer)
  - Jumps to the program entry point
- Implement a transpiler to convert trained model operations (or a small subset thereof) into sequences of ISA instructions that call the neural primitives.

### Verification & Testing
- Automated test harness for black‑box testing:
  - Given character input, run the emulator and verify framebuffer output matches expected results.
  - Regression tests for instruction semantics, numerical correctness, and device behavior.
- Use LLM assistance to generate test cases and to help write portions of the emulator/bootloader, but maintain strict human review for correctness.

## Deliverables
- Formal ISA specification (documented instruction set, encodings, memory map).
- Assembler for the ISA and example assembly programs.
- Emulator binary/source with:
  - CPU implementation of ISA and neural primitives
  - Character input and framebuffer devices
  - Loader/boot sequence
- Model conversion tool (PyTorch → emulator memory format).
- Training scripts and at least one trained model used in demonstrations.
- Test suite (unit tests for ISA, black-box tests for end-to-end tasks).
- Project report and demo
- Functional: system can load a trained model and render expected framebuffer output for test inputs.

## Stretch goals
- Add communication device to interact with another emulator instance (network-like link).
- LLM-generated fake device datasheet used to create training material and a follow-up model.
- Extend ISA with more advanced tensor ops (convolution, pooling).
- Support simple on‑emulator training (online fine-tuning) for tiny models.

## Risks and mitigations
- Risk: numerical instability / precision issues in reduced-precision inference.
  - Mitigation: start with float32 reference implementation, then add quantization with careful calibration and tests.
- Risk: scope creep (too many ISA features).
  - Mitigation: maintain a strict minimal core and treat additional features as stretch goals.
- Risk: LLM-generated code may contain subtle bugs.
  - Mitigation: require human review, unit tests, and deterministic test vectors.
