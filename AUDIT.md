# Project Audit

**Project:** Neural-Driven Computing on Minimal RISC-V Stack
**Course:** ASE2026
**Last audited:** 2026-06-19 (full re-audit with LLM/AI integrity checks)
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
| Is there measurable evidence? | ✅ | 26.67x speedup (RTL PMAC4), 2000x speedup (C++ backend), deterministic output parity, cycle thresholds from `phase25-neural-lane-cycle-comparison.json`. |
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
| Are there tests? | ✅ | 292 unit tests (13 test executables) + 91 blackbox test files |
| Are critical paths covered? | ✅ | Neural operations, syscalls, edge cases, RTL parity. |

**Verified by building and running:**
```bash
cmake -S projects/emulator -B projects/emulator/build  # ✅ configured
cmake --build projects/emulator/build -j$(nproc)        # ✅ built
# Unit tests: 19+12+24+33+15+81+5+27+10+18+19+25+4 = 292 PASSED
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
| Does it follow IEEE format? | ⚠️ | Compliant structure. Missing "Acknowledgment" section. |

### Figures and Diagrams

| Question | Status | Evidence |
|----------|--------|----------|
| Are figures clear and readable? | ✅ | 4 TikZ figures: system architecture, descriptor layout, block-diagonal composition, benchmark chart. |
| Do figures support the text? | ✅ | Each figure referenced in text with `\ref{}`. |
| Are captions descriptive? | ✅ | Captions explain content and context. |

### References

| Question | Status | Evidence |
|----------|--------|----------|
| Are all claims properly cited? | ✅ | All technical claims have citations. |
| Are references relevant? | ✅ | 17 references, all relevant to the work. |
| Are references properly formatted? | ✅ | IEEE format with authors, titles, venues, DOIs. Some arXiv-only refs lack DOIs (expected). |
| Is the reference list complete? | ✅ | Includes RISC-V, Verilator, PyTorch, related work. |
| Do references exist (not hallucinated)? | ✅ | All 17 references verified online. |
| Do details match reality? | ✅ | Authors, venues, years match actual publications. |

**Rating:** 7/10 — Well-structured and clearly written. References fixed and verified. Some arXiv-only refs remain (not author's fault). Missing "Acknowledgment" section.

---

## Problem Definition and Research Question

| Question | Status | Evidence |
|----------|--------|----------|
| Is the research question explicitly stated? | ✅ | "How far can a compact execution stack be pushed when neural operations are represented as first-class ISA extensions on a minimal RISC-V core?" (`documentation/ase2026.md:39-41`) |
| Is the problem well-motivated? | ✅ | Gap in literature: No prior work demonstrates lightweight MLP-based execution on bare-metal RISC-V. Real-world need: Resource-constrained edge devices. |
| Does the contribution address the problem? | ✅ | Descriptor-based neural ISA, block-diagonal composition, dual-backend validation, OS-like task switching. |
| Is the scope clearly defined? | ✅ | Minimal RISC-V cores, MLP-based inference, end-to-end toolchain, deterministic validation. |
| Are limitations discussed? | ✅ | No traditional OS, static model composition, single-threaded, no interrupts, limited I/O. |
| Is the research question measurable? | ✅ | Speedup (26.67x RTL, 2000x C++), deterministic output, cycle thresholds, model composition overhead. |
| Do results answer the research question? | ✅ | Demonstrates neural inference as primary execution model, descriptor-based ISA, model composition, OS-like task switching, dual-backend validation. |

**Rating:** 9/10 — Research question is explicit, well-motivated, and measurable. Results directly answer the question.

---

## Code Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Is error handling robust? | ✅ | Comprehensive validation in `NeuralOps.cpp` and `Emulator.cpp`. Checks for invalid pointers, unaligned access, overflow, NaN. |
| Are there hardcoded paths? | ⚠️ | Model paths, test data paths, framebuffer dimensions, syscall numbers. |
| Is test coverage sufficient? | ✅ | 292 unit tests + 91 blackbox tests. Covers neural operations, syscalls, edge cases. |
| Any stale TODO/FIXME? | ✅ | Only 1 TODO in a test file (`test_simple_layer.s:50`), not in production code. |

**Rating:** 8/10 — Robust error handling and test coverage. Hardcoded paths need attention.

---

## LLM/AI Use in Academic Writing

| Question | Status | Evidence |
|----------|--------|----------|
| Is AI use disclosed in the paper? | ⚠️ | No AI use disclosure statement found in the paper. |
| Are AI-generated claims verified against primary sources? | ✅ | All technical claims traceable to source code and benchmark data. |
| Are AI-generated citations independently verified? | ✅ | All 17 references verified online with correct authors, titles, venues. |
| Can the author demonstrate individual contribution? | ✅ | Git history shows consistent development over multiple phases. Codebase is coherent and internally consistent. |
| Does the paper avoid AI red flags? | ✅ | Writing shows natural variation, specific technical details, project-specific examples. No generic language or phantom citations. |
| Are technical claims traceable to codebase? | ✅ | Speedup claims verified against `phase25-neural-lane-cycle-comparison.json`. ISA instructions match `Instruction.{h,cpp}`. |
| Is the paper internally consistent? | ⚠️ | **One inaccuracy found:** Paper claims runtime.c is "141 lines" (`ase2026.md:44,183,513`) but actual file is 162 lines. |

**Red Flags Check:**

| Category | Status | Notes |
|----------|--------|-------|
| Tone consistency | ✅ | Natural variation, not overly uniform |
| Structure | ✅ | Varied paragraph structure, not formulaic |
| Specificity | ✅ | Concrete project details, not generic |
| Citations | ✅ | All verified, no phantom references |
| Factual accuracy | ⚠️ | runtime.c line count is inaccurate (141 vs 162) |
| Voice | ✅ | Author's technical perspective comes through |
| Imperfections | ✅ | Minor natural imperfections present |

**Academic Integrity Assessment:**
- The paper demonstrates deep domain knowledge specific to the project
- All claims are traceable to verifiable sources (code, benchmarks, tests)
- Writing style is consistent with a technical master's thesis
- No evidence of wholesale AI generation
- The single factual inaccuracy (runtime.c line count) appears to be a minor error, not evidence of AI fabrication

**Rating:** 7/10 — No AI disclosure found, but content is well-verified and shows genuine author engagement. One factual inaccuracy needs correction.

---

## Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Research Quality | 9/10 | Highly novel contributions with strong evidence and impact. Related work comparison could expand. |
| Implementation Quality | 9/10 | Fully functional pipeline with comprehensive testing. Partial RTL support for combined models. |
| Documentation Quality | 9/10 | Comprehensive, accurate, and machine-readable. Minor redundancy in build instructions. |
| Paper Quality | 7/10 | Well-structured and clearly written. References fixed and verified. Missing "Acknowledgment" section. |
| Problem Definition | 9/10 | Research question is explicit, well-motivated, and measurable. Results directly answer the question. |
| Code Quality | 8/10 | Robust error handling and test coverage. Hardcoded paths need attention. |
| LLM/AI Integrity | 7/10 | No AI disclosure, but content verified and shows genuine authorship. One factual inaccuracy. |
| **Overall** | **8.3/10** | Strong project with verified references and code. Minor issues: runtime.c line count, no AI disclosure, missing Acknowledgment. |

---

## Recommendations for Improvement

### High Priority
1. **Correct runtime.c line count** — Paper claims 141 lines, actual is 162 lines. Fix in `ase2026.md:44,183,513`.
2. **Add AI Use Disclosure** — Even if no AI was used, a brief statement (e.g., "The author did not use AI tools in writing this paper") is good practice per university guidelines.
3. **Add "Acknowledgment" section** — Required by IEEE format. Include supervisor acknowledgment.

### Medium Priority
4. **Expand related work** with more recent papers (2025-2026) and non-RISC-V accelerators (e.g., Google Edge TPU).
5. **Add a "Limitations" subsection** to the paper to discuss trade-offs (e.g., block-diagonal composition vs. learned merging).
6. **Improve RTL support** for combined models (e.g., `counter+chargen`).
7. **Add benchmarks** for neural operations and syscall overhead.

### Low Priority
8. **Add a "Getting Started" guide** for new contributors.
9. **Consolidate build instructions** into a single `BUILD.md` file.
10. **Add JSON Schema files** for glue/model JSON to enable automated validation.
11. **Define all acronyms** (e.g., "NRAL") in the paper.

---

## Next Audit

- **After line count fix:** Verify runtime.c claim is corrected.
- **After major changes:** Re-run full test suite, verify documentation, and update audit.
- **Before publication:** Full audit with checklist from `AUDIT_GUIDE.md`. Ensure IEEE compliance and address all high-priority recommendations.
- **Quarterly:** Quick check of build/test/docs and code quality.
