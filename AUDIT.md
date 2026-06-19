# Project Audit

**Project:** Neural-Driven Computing on Minimal RISC-V Stack
**Course:** ASE2026
**Last audited:** 2026-06-19 (references fixed)
**How to audit:** See `AUDIT_GUIDE.md`

---

## Research Quality

### Novelty and Contributions

| Question | Status | Evidence |
|----------|--------|----------|
| What is the novel contribution? | ✅ | Descriptor-based neural ISA, block-diagonal model composition, dual-backend validation, OS-like neural task switching |
| Is the research question explicitly stated? | ✅ | "How far can a compact execution stack be pushed when neural operations are represented as first-class ISA extensions on a minimal RISC-V core?" (`documentation/ase2026.md:39-41`) |
| Is the problem well-motivated? | ✅ | Gap in literature: No prior work demonstrates lightweight MLP-based execution on bare-metal RISC-V. Real-world need: Resource-constrained edge devices. |
| Are contributions novel and significant? | ✅ | Descriptor-based neural ISA and OS-like task switching are highly novel. Block-diagonal composition and dual-backend validation are significant advancements. |

### Related Work

| Question | Status | Evidence |
|----------|--------|----------|
| How does it compare to related work? | ✅ | Compares to RV-SCNN, MARVEL, nCPU, and embodiOS. Differentiates with descriptor-based abstraction, MLP focus, and dual-backend validation. |
| Is the comparison thorough? | ⚠️ | Descriptive but lacks critical depth. No comparison to non-RISC-V accelerators (e.g., Google Edge TPU). |

### Evidence and Impact

| Question | Status | Evidence |
|----------|--------|----------|
| Is there measurable evidence? | ✅ | 2000x speedup (C++ backend), 26.67x speedup (RTL), deterministic output parity, cycle thresholds. |
| Is the evidence convincing? | ✅ | Strong quantitative results with rigorous testing (unit, blackbox, differential). |
| What is the impact potential? | ✅ | Edge AI, tiny RISC-V cores, neural-as-OS pattern, reproducibility. |

**Rating:** 9/10 — Highly novel contributions with strong evidence and impact. Related work comparison could be expanded.

---

## Implementation Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Does the end-to-end pipeline work? | ✅ | train → export → compile → assemble → run (fully functional) |
| Are both backends functional? | ✅ | emulator_runner + verilator_runner (bit-exact parity for single models) |
| Is there CI/CD? | ✅ | `.github/workflows/emulator-tests.yml` (automated build, test, validation) |
| Are there tests? | ✅ | ~460 unit tests, blackbox tests, differential tests, interactive tests |
| Are critical paths covered? | ✅ | Neural operations, syscalls, edge cases, RTL parity. |

**How to verify:**
```bash
cmake -S projects/emulator -B projects/emulator/build
cmake --build projects/emulator/build -j$(nproc)
ctest --test-dir projects/emulator/build --output-on-failure
```

**Rating:** 9/10 — Fully functional pipeline with comprehensive testing. Partial RTL support for combined models.

---

## Documentation Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Is there a clear project overview? | ✅ | `README.md`, `projects/emulator/AGENTS.md` (detailed, accurate, well-structured) |
| Are build instructions accurate? | ✅ | `projects/emulator/BUILD_DIRECTORY.md`, `projects/emulator/AGENTS.md` (functional, up-to-date) |
| Is architecture documented? | ✅ | `projects/emulator/COMBINING.md`, `projects/emulator/combined-mlp.md` (clear, detailed, aligned with implementation) |
| Are code conventions followed? | ✅ | No comments unless asked (exceptions justified by complexity). Consistent patterns. |
| Is documentation machine-readable? | ✅ | Structured tables, JSON formats, ASCII diagrams, consistent formatting. |

**Rating:** 9/10 — Comprehensive, accurate, and machine-readable. Minor redundancy in build instructions.

---

## Paper Quality

### Structure

| Question | Status | Evidence |
|----------|--------|----------|
| Does the abstract clearly state problem, approach, results? | ✅ | `documentation/ase2026.md:15-25` — Problem, approach, 2000x speedup. |
| Does the introduction motivate the research? | ✅ | `documentation/ase2026.md:35-68` — Motivation, 4 contributions. |
| Is related work properly positioned? | ✅ | `documentation/ase2026.md:70-110` — 3 subsections with comparison. |
| Is the methodology clearly described? | ✅ | `documentation/ase2026.md:111-175` — System architecture, descriptor-based ISA, model composition. |
| Are results properly presented? | ✅ | `documentation/ase2026.md:386-435` — Benchmarks, validation, speedup. |
| Does the conclusion summarize contributions? | ✅ | `documentation/ase2026.md:436-459` — 5 key findings, future work. |

### Writing Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Is the writing clear and concise? | ✅ | Technical depth balanced with readability. |
| Are there grammatical errors? | ✅ | No significant errors. |
| Is terminology consistent? | ✅ | Consistent use of "descriptor-based", "block-diagonal", "neural-as-OS". |
| Are acronyms defined? | ⚠️ | Mostly compliant. Some acronyms (e.g., "NRAL") are undefined. |
| Does it follow IEEE format? | ⚠️ | Compliant structure. Missing "Acknowledgment" section. References not IEEE-formatted. |

### Figures and Diagrams

| Question | Status | Evidence |
|----------|--------|----------|
| Are figures clear and readable? | ⚠️ | No figures in paper. Diagrams in `COMBINING.md` are ASCII-based. |
| Do figures support the text? | ❌ | N/A — no figures in paper. |
| Are captions descriptive? | ❌ | N/A — no figures in paper. |

**Recommendations:**
- Add figures to paper:
  - System architecture diagram.
  - Neural ISA descriptor layout.
  - Block-diagonal composition diagram.
  - Benchmark results chart.

### References

| Question | Status | Evidence |
|----------|--------|----------|
| Are all claims properly cited? | ✅ | All technical claims have citations. |
| Are references relevant? | ✅ | 17 references, all relevant to the work. |
| Are references properly formatted? | ⚠️ | Partially fixed. Most references now in IEEE style. Some arXiv-only refs lack DOIs (expected). |
| Is the reference list complete? | ✅ | Includes RISC-V, Verilator, PyTorch, related work. |
| Do references exist (not hallucinated)? | ✅ | All external references verified to exist online. |
| Do details match reality? | ✅ | Fixed: authors, venues, years now match actual publications. |

**Detailed Reference Verification (2026-06-19, updated):**

| Ref | Status | Notes |
|-----|--------|-------|
| [1] RISC-V International | ✅ | Verified. URL correct. |
| [2] Verilator | ✅ | Verified. URL correct. |
| [3] PyTorch | ✅ | Verified. NeurIPS 2019 correct. |
| [4] GNU Binutils | ✅ | Verified. URL correct. |
| [5] Repository artifact | ✅ | Internal ref. File exists. |
| [6] Repository source | ✅ | Internal ref. Files exist. |
| [7] Repository source | ✅ | Internal ref. Files exist. |
| [8] FS-Merge | ✅ | Fixed. Authors: Kinderman, Hubara, Maron, Soudry. TMLR 2025. |
| [9] LoRA-LEGO | ✅ | Fixed. Authors: Zhao, Shen, Zhu, Li, Su, Wang, Wu. ICLR 2025. |
| [10] mergekit | ✅ | Fixed. Goddard et al., EMNLP 2024 Industry Track, pp. 477-485. |
| [11] nCPU | ⚠️ | No peer-reviewed publication. GitHub repo cited as preprint. |
| [12] RV-SCNN | ✅ | Verified. IEEE TCAD, vol. 44, no. 4, pp. 1567-1580, Apr. 2025. |
| [13] MARVEL | ✅ | Fixed. IEEE OJCAS, vol. 6, pp. 445-456, 2025. |
| [14] FPGA-Accelerated RISC-V | ✅ | Verified. arXiv:2511.06955, Nov. 2025. |
| [15] VMXDOTP | ✅ | Fixed title to uppercase. arXiv:2603.04979, Mar. 2026. |
| [16] Mixed-precision RISC-V | ✅ | Fixed. ICCAD '24, DOI: 10.1145/3676536.3676840. |
| [17] Ultra-Low-Power RISC-V | ✅ | Fixed. Chips, vol. 4, no. 2, p. 13, 2025. DOI added. |

**Remaining Issues:**
- [11] nCPU is not peer-reviewed (GitHub markdown paper only)
- [14] FPGA-Accelerated RISC-V is arXiv-only (no journal publication yet)
- [15] VMXDOTP is arXiv-only (accepted at DATE '26 but not yet published)

**Rating:** 5/10 — Multiple author and venue errors. No IEEE formatting. Requires correction before publication.

---

## Problem Definition and Research Question

| Question | Status | Evidence |
|----------|--------|----------|
| Is the research question explicitly stated? | ✅ | "How far can a compact execution stack be pushed when neural operations are represented as first-class ISA extensions on a minimal RISC-V core?" (`documentation/ase2026.md:39-41`) |
| Is the problem well-motivated? | ✅ | Gap in literature: No prior work demonstrates lightweight MLP-based execution on bare-metal RISC-V. Real-world need: Resource-constrained edge devices. |
| Does the contribution address the problem? | ✅ | Descriptor-based neural ISA, block-diagonal composition, dual-backend validation, OS-like task switching. |
| Is the scope clearly defined? | ✅ | Minimal RISC-V cores, MLP-based inference, end-to-end toolchain, deterministic validation. |
| Are limitations discussed? | ✅ | No traditional OS, static model composition, single-threaded, no interrupts, limited I/O. |
| Is the research question measurable? | ✅ | Speedup (2000x), deterministic output, cycle thresholds, model composition overhead. |
| Do results answer the research question? | ✅ | Demonstrates neural inference as primary execution model, descriptor-based ISA, model composition, OS-like task switching, dual-backend validation. |

**Rating:** 9/10 — Research question is explicit, well-motivated, and measurable. Results directly answer the question.

---

## Code Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Is error handling robust? | ✅ | Comprehensive validation in `NeuralOps.cpp` and `Emulator.cpp`. Checks for invalid pointers, unaligned access, overflow, NaN. |
| Are there hardcoded paths? | ⚠️ | Model paths, test data paths, framebuffer dimensions, syscall numbers. |
| Is test coverage sufficient? | ✅ | ~460 unit tests, blackbox tests, differential tests, interactive tests. Covers neural operations, syscalls, edge cases. |
| Any stale TODO/FIXME? | ⚠️ | 4 active TODOs (dynamic input handling, framebuffer capture, output mapping). |

**Rating:** 8/10 — Robust error handling and test coverage. Hardcoded paths and TODOs need attention.

---

## Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Research Quality | 9/10 | Highly novel contributions with strong evidence and impact. Related work comparison could expand. |
| Implementation Quality | 9/10 | Fully functional pipeline with comprehensive testing. Partial RTL support for combined models. |
| Documentation Quality | 9/10 | Comprehensive, accurate, and machine-readable. Minor redundancy in build instructions. |
| Paper Quality | 7/10 | Well-structured and clearly written. References fixed. Some arXiv-only refs remain. Still missing figures. |
| Problem Definition | 9/10 | Research question is explicit, well-motivated, and measurable. Results directly answer the question. |
| Code Quality | 8/10 | Robust error handling and test coverage. Hardcoded paths and TODOs need attention. |
| **Overall** | **8.5/10** | Strong project with references fixed. Remaining: add figures, address arXiv-only refs. |

---

## Recommendations for Improvement

### High Priority
1. **Add figures to the paper** (architecture diagram, benchmark chart).
2. **Fix 4 active TODOs** in the codebase (dynamic input handling, framebuffer capture, output mapping).
3. **Replace hardcoded paths** with environment variables or CLI arguments.

### Medium Priority
5. **Expand related work** with more recent papers (2025-2026) and non-RISC-V accelerators (e.g., Google Edge TPU).
6. **Add a "Limitations" subsection** to the paper to discuss trade-offs (e.g., block-diagonal composition vs. learned merging).
7. **Improve RTL support** for combined models (e.g., `counter+chargen`).
8. **Add benchmarks** for neural operations and syscall overhead.

### Low Priority
9. **Add a "Getting Started" guide** for new contributors.
10. **Consolidate build instructions** into a single `BUILD.md` file.
11. **Add JSON Schema files** for glue/model JSON to enable automated validation.
12. **Define all acronyms** (e.g., "NRAL") in the paper.

---

## Next Audit

- **After reference fixes:** Re-verify all 17 references, confirm IEEE formatting, check author/venue/year corrections.
- **After major changes:** Re-run full test suite, verify documentation, and update audit.
- **Before publication:** Full audit with checklist from `AUDIT_GUIDE.md`. Ensure IEEE compliance and address all high-priority recommendations.
- **Quarterly:** Quick check of build/test/docs and code quality.
