# ASE 2026 — Neural-driven Computing
Bernhard Guillon

## Introduction
Modern large language models and AI toolchains typically run inside heavy software stacks (OS + browser + runtime). Many applications will increasingly embed neural components at many layers of the stack. This project explores whether we can design a far more lightweight computing environment that can directly host perceptron-based neural models as first-class computational elements.

We propose to define a minimal instruction set (ISA) with a small set of neural/tensor primitives, implement an emulator for that ISA, and run small trained networks directly in the emulator. The effort covers ISA design, assembler/loader, model-to-ROM/memory serialization, and verification tooling (including automated black‑box tests).

## Vision
Create a compact, demonstrable platform where:

A tiny neural model (e.g., a perceptron or small MLP) can be loaded and executed by a minimal runtime / emulator.

The ISA is RISC-like (RISC-V inspired) and extended with a few neural-tensor primitives (matmul, activation, tensor ops).

I/O is minimal: character input (keyboard-like device) and a simple framebuffer output. The pipeline is:
  Keyboard input → neural model inference → Framebuffer pixel output

The initial demonstration task: train a model that receives short character input and produces a corresponding framebuffer output (e.g., render text or glyphs). The emulator should be capable of loading the model into memory and running inference using the extended ISA.

### Use of AI
Use LLM to help with research on the ISA, create AI training data. Also write the emulator for the ISA a bootloader and an assembler. We might also need a "transpiler" to transform the model to something which we can load. Or write our own model creator.
