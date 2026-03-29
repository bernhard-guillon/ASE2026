# ASE2026 Project Log

This log consolidates the previous phase summaries, planning notes, review artifacts, and emulator documentation into a single, presentation-ready project history.

## Project Scope

ASE2026 builds a neural-driven execution stack on a minimal RISC-V environment:

- model export from PyTorch
- model compiler and binary embedding
- custom assembler + GNU link flow
- emulator and Verilator backends
- iterative custom neural instruction optimization (x77, x7b, PMAC variants)
- differential verification and benchmark-based tuning

The character-recognition branch was removed and is not part of the final scope.

## Consolidated Timeline

## Phase A - Foundation and Core Emulator

- RV32I emulator modules implemented (CPU, memory, decode/execute, loader).
- Unit and blackbox test infrastructure established.
- Core behavior validated with CTest.

## Phase B - C Runtime and Syscall Growth

- Linux-style syscall support expanded (write/exit and later file/memory syscalls).
- C program execution support added with crt0/syscall plumbing.
- File I/O, heap, mmap/munmap paths tested via blackbox C suites.

## Phase C - Weight Export and Memory Integration

- PyTorch to JSON to binary export pipeline implemented in `projects/weight-export/`.
- Binary model format standardized (header + layer table + float payload).
- Model loading/memory-layout verification added (C++ + RISC-V-side checks).

## Phase D - Neural Execution Pipeline

- Neural compiler emits assembly with embedded model payloads.
- Runtime path established:
  - character code input
  - one-hot mapping
  - dense forward pass + activation
  - framebuffer output
- End-to-end neural execution validated in emulator.

## Phase E - GUI and Interactive Workflows

- GUI/interactive runner workflows added for neural visualization.
- Character-driven framebuffer rendering and manual QA scripts documented.

## Phase F - ISA Extension Iterations (x77 -> x7b)

- Custom instruction flow evolved from x77 to x7b variants.
- Lane/PMAC progression introduced:
  - `x7b-base`
  - `x7b-4lane`
  - `x7b-8lane`
  - `x7b-8lane-pmac`
  - `x7b-8lane-pmac2`
  - `x7b-8lane-pmac3`
  - `x7b-8lane-pmac4`

## Phase G - Verification, Parity, and Performance Hardening

- Differential validation between `emulator_runner` and `verilator_runner` used as a gate.
- Assembler parity scaffolding maintained against GNU workflows.
- Final PMAC4 variant delivered the strongest Verilator cycle-threshold reduction.

## Benchmark Highlights (Consolidated)

Data source moved to `documentation/collected-data/`.

| Milestone | Key Result |
| --- | --- |
| Phase 1 baseline vs x77 | C++ backend `1500x`, Verilator backend `4.0x` |
| Phase 7 enhanced x7b base | C++ enhanced vs baseline `2000x`, Verilator `5.333x` |
| Phase 14/21 lane analysis | 4-lane -> 8-lane observed scaling `1.0x` (efficiency `0.5`, ideal `2.0x`) |
| Phase 25 PMAC4 | Verilator threshold `400k -> 200k -> 150k`; PMAC4 vs 8-lane `2.67x`; PMAC4 vs PMAC/PMAC2/PMAC3 `1.33x` |

## Current Quality Gates

- Emulator clean rebuild and full test run is passing:
  - `cmake -S projects/emulator -B projects/emulator/build -DCMAKE_BUILD_TYPE=Release`
  - `cmake --build projects/emulator/build -j4`
  - `ctest --test-dir projects/emulator/build --output-on-failure`
- Character-generation pipeline is validated via virtualenv install + smoke train/inference.

## Canonical Documentation After Cleanup

- Project chronology and consolidated summaries:
  - `documentation/project-log.md` (this file)
- Neural machine and ISA/memory reference:
  - `documentation/neural-risc-v-machine.md`
- Research/benchmark JSON data:
  - `documentation/collected-data/*.json`
- IEEE paper draft:
  - `documentation/ase2026.md`

## Merged Source Documents (Traceability)

The following historical docs were consolidated into this log and removed as standalone summary/planning artifacts:

- `AI_IMPLEMENTATION_PLAN.md`
- `MANUAL_TESTING_GUIDE.md`
- `NEURAL_TEST_SUMMARY.md`
- `PHASE1_COMPLETE.md`
- `QUICK_START.md`
- `VERIFICATION_SUMMARY.md`
- `docs/research/speedup-naive-vs-first-improovement.md`
- `projects/weight-export/IMPLEMENTATION_NOTES.md`
- `projects/weight-export/PHASE1_SUMMARY.md`
- `projects/character-generation/HOW_TO_REVIEW.md`
- `projects/character-generation/PYTORCH_CHARACTER_MAP.md`
- `projects/character-generation/PYTORCH_MODEL_REVIEW.md`
- `projects/character-generation/PYTORCH_VS_STATIC_COMPARISON.md`
- `projects/character-generation/README_PYTORCH_OUTPUT.md`
- `projects/emulator/GUI_TESTING_GUIDE.md`
- `projects/emulator/INTERACTIVE_NEURAL_CHARGEN.md`
- `projects/emulator/PHASE4_SUMMARY.md`
- `projects/emulator/PHASE5_COMPLETE.md`
- `projects/emulator/PHASE5_GUI_INTEGRATION.md`
- `projects/emulator/plan.md`
- `projects/emulator/docs/` (guides, planning notes, summaries)
