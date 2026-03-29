# Neural RISC-V Machine

This document unifies the neural ISA notes, execution model, and memory map for the ASE2026 neural execution stack.

## Purpose

Define the machine-level contract for neural execution on the emulator/RTL pair:

- memory layout and ownership
- model binary format placement
- execution dataflow
- custom neural instruction semantics
- determinism and validation rules

## High-Level Execution Flow

`a0 character -> one-hot input -> dense layers -> activation -> clamp/u8 -> framebuffer`

Current generation-oriented pipeline:

- Dense (255x256) + ReLU
- Dense (256x256) + ReLU
- Dense (256x400) + piecewise sigmoid
- clamp/scale to 0..255 and write framebuffer bytes

## Memory Map (Consolidated)

Address ranges are byte-addressed and little-endian.

- `0x00000000 - 0x00000FFF`: null-guard/trap region
- `0x00001000 - 0x0000FFFF`: code section / runtime stubs
- `0x00010000 - 0x0010FFFF`: generator model image
- `0x00110000 - 0x0014FFFF`: reserved model region (legacy allocation, currently unused)
- `0x00150000 - 0x00153FFF`: neural input/activation/output buffers
- `0x00200000 - 0x003FFFFF`: framebuffer region
- `0x00400000+`: heap and dynamic mappings
- high memory: stack region (downward growth)

## Model Binary Layout in Memory

Model image layout:

1. Header (magic/version/model_type/layer_count/counts)
2. Layer table entries
3. Packed float32 weights
4. Packed float32 biases

Historical notes mention both `0x4E52414E` and `0x4E52414C` variants in older docs;
current loader/format behavior should be validated against live code when changing format.

## Neural Instruction Set (Project-Specific)

The project evolved from early NEURAL_FC concepts to structured x77/x7b custom ops.
The semantic intent is preserved here in operation form.

### Core operation families

- MatVec (dense layer kernel)
- ReLU vector activation
- Piecewise-sigmoid vector activation
- Clamp+scale float-to-u8 conversion

### Instruction behavior contracts

- deterministic for equal initial state and inputs
- explicit error signaling for invalid descriptors/flags/pointers
- no silent partial writes on precondition failure
- f32 alignment required where applicable

### Piecewise sigmoid (compatibility behavior)

- `x <= -4.0 -> 0.0`
- `x >=  4.0 -> 1.0`
- otherwise `0.5 + x*0.125`

This approximation is intentional to match project execution behavior and avoid heavy transcendental math in the core path.

## x77/x7b Evolution Summary

Custom op rollout:

- x77 baseline custom neural path
- x7b enhanced path with lane progression
- PMAC variants culminating in PMAC4 (`nmatvec8xp4`)

Benchmark data shows PMAC4 delivering the strongest Verilator-cycle threshold reduction while preserving deterministic framebuffer parity.

## Runtime Buffer Conventions

Typical working buffers:

- input vector buffer (one-hot / source activations)
- ping/pong activation buffers for layer chaining
- output buffer for final layer
- framebuffer byte target buffer

## Determinism and Validation

Required validation layers:

- parser/encoder tests for custom instructions
- blackbox compiler/assembler checks
- emulator vs Verilator differential comparison
- full CTest regression gate before integration

## Practical Build/Run Commands

```bash
cmake -S projects/emulator -B projects/emulator/build -DCMAKE_BUILD_TYPE=Release
cmake --build projects/emulator/build -j4
ctest --test-dir projects/emulator/build --output-on-failure
```

For benchmark datasets and cycle-comparison artifacts, see:

- `documentation/collected-data/phase*.json`

## Sources Consolidated Into This Document

- `NEURAL_FC.md`
- `projects/emulator/docs/guides/NEURAL_OPS_PROGRAMMER_MANUAL.md`
- `projects/emulator/docs/guides/NEURAL_INSTRUCTION_REFERENCE.md`
- `projects/emulator/docs/guides/NEURAL_EXECUTION_GUIDE.md`
- memory-map notes from `projects/weight-export/README.md`
- session memory map artifact `files/MEMORY_MAP.txt`
