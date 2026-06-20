# Project Audit

**Project:** Neural-Driven Computing on Minimal RISC-V Stack
**Course:** ASE2026
**Last audited:** 2026-06-20 (post-fix re-audit: all 6 paper data-fixes verified; build + 460 ctests re-run; remaining issues inventory)
**Audit workflow:** `AUDIT_GUIDE.md`
**Auditor:** opencode (AI agent), acting as external examiner

---

## How to Read This Audit

Each dimension is rated independently. A fix status column tracks the 6 critical
data-integrity fixes applied in commits `d5ad4b8..a3f8063`. Remaining open items
are listed under Code Quality and at the bottom of the paper section.

---

## Research Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Novel contribution? | ✅ | Descriptor-based neural ISA, training-free block-diagonal MLP composition, dual-backend (C++/Verilator) bit-exact validation on bare-metal RISC-V. |
| Related work positioning? | ✅ | 20 references across RISC-V neural ISAs, accelerators, model merging, and AI-as-OS. Four comparison tables clearly differentiate. |
| Measurable evidence? | ✅ | 460 tests pass; cycle thresholds in `phase25*.json`; 100% exact-match confirmed in `movement_metrics.json`. |
| Overclaiming? | ⚠️ | "Neural inference replaces the operating system" is an ambitious framing. The runtime is a 162-line inference loop; "multitasking" is cooperative single-threaded gating. The paper's own Limitations section concedes this, but the abstract/intro headings lean heavily on the OS metaphor. |

**Rating:** 8/10 — Genuinely novel approach with strong positioning. OS-replacement rhetoric remains rhetorically heavy for what is demonstrated.

---

## Problem Definition and Research Question

| Question | Status | Evidence |
|----------|--------|----------|
| RQ explicitly stated? | ✅ | "whether a minimal RISC-V system can use neural inference as its primary computation model" (`ase2026.md:36-38`). |
| Traceable thread? | ✅ | Problem (abstract) → RQ (intro) → methodology (ISA, composition, router) → evaluation (benchmarks, accuracy, parity) → conclusion. |
| Measurable? | ✅ | Speedup, deterministic parity, accuracy, cycle thresholds. |
| Scope drift? | ✅ | No. |

**Rating:** 8.5/10

---

## Implementation Quality

| Question | Status | Evidence |
|----------|--------|----------|
| End-to-end pipeline works? | ✅ | Clean build; train→export→compile→assemble→run exercised by blackbox tests. |
| Both backends functional? | ✅ | `emulator_runner` + `verilator_runner`; `verilator/*` and `differential` ctest groups pass. |
| CI/CD? | ✅ | `.github/workflows/emulator-tests.yml`. |
| Tests pass? | ✅ | **460/460 ctests pass** (0 failed). Includes 51 parity, 9 verilator, 27 neural, 1 differential. |

**Rating:** 9/10

---

## Documentation Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Project overview? | ✅ | `README.md`, `AGENTS.md`, per-project `AGENTS.md`. |
| Build instructions accurate? | ✅ | `BUILD.md` / `AGENTS.md` commands reproduce the build verbatim. |
| Architecture docs? | ✅ | `COMBINING.md`, `combined-mlp.md`, schemas under `schemas/`. |
| Machine-readable? | ✅ | Structured tables, JSON, schemas. |
| Self-audit accurate? | ⚠️ | This is the 4th revision of AUDIT.md. Each revision has corrected mis-statements from the prior one. Care should be taken that the audit tracks the actual artifacts, not prior audit language. |

**Rating:** 8/10

---

## Paper Quality

### Fixes Applied (commits d5ad4b8..a3f8063)

Each of these was verified to match the cited data in this re-audit:

| # | Issue | Fix commit | Status |
|---|-------|-----------|--------|
| 1 | Threshold-sensitivity table reported *probed* values instead of passing thresholds | `d5ad4b8` | ✅ C++ now 1,500 (const); Verilator 400k→150k; caption corrected to 2.67× |
| 2 | Benchmark chart C++ x7b-8lane plotted 1500× (x77 speedup) instead of 2000× | `42f9d18` | ✅ |
| 3 | Router architecture inconsistent: intro/figure said 2→4→2→2, accuracy table said 2→16→2→2, code is 2→16→2 | `dc4227f` | ✅ All 5 occurrences now 2→16→2 |
| 4 | Abstract claimed "100% model accuracy" — only discrete-output models hit 100%, chargen is MSE-converged, renderer 99.99% | `25da024` | ✅ Now "near-perfect model accuracy (100% exact match on discrete-output models, 99.99% pixel accuracy on the renderer)" |
| 5 | Ref [13] MARVEL dressed as *IEEE OJCAS* vol.6 pp.445–456 with arXiv DOI — unverifiable | `12da979` | ✅ Now cited as arXiv:2508.01800 with "to be published" note |
| 6 | AI disclosure did not name tools | `a3f8063` | ✅ Now lists MiMo, DeepSeek, Mistral, Claude Haiku, Claude Opus, Codex |

### Remaining Paper Issues (not blocking)

| Issue | Severity | Note |
|-------|----------|------|
| OS-replacement rhetoric oversells what is demonstrated | 🟡 Low | Fixable by toning language, but the Limitations section already covers this. |
| Pervasive bold-emphasis in abstract/intro/OS taxonomy reads as AI-generated copy | 🟢 Cosmetic | Natural scientific prose would use bold sparingly. |

### Structure & Writing

Well-organized IEEE-format paper, **9 pages** (within the 10-page limit). All acronyms defined; terminology consistent. Figures (13 `figure`/`table` environments) are captioned and referenced.

### References

All of [8]–[20] plus the informal AI-as-OS projects (embodiOS, OSymbiote, OO) independently verified online in this audit session — **no hallucinated citations**.

| Ref | Status | Note |
|-----|--------|------|
| [13] MARVEL | ✅ | Fixed — now cited as arXiv preprint with "to be published" note. |
| [11] nCPU | ℹ️ | Real GitHub repo; subtitle is a paraphrase. Non-peer-reviewed (acceptable as software citation). |
| All others | ✅ | Authors, titles, years, venues, DOIs verified correct. |

**Rating:** 8/10 — Upgraded from 6/10 after the 6 data fixes. No wrong numbers remain in tables. Some prose style choices remain but are not blocking.

---

## Code Quality

| Question | Status | Evidence |
|----------|--------|----------|
| Error handling robust? | ✅ | `NeuralOps.cpp` bounds-checks, NaN handling (`std::isnan`), saturation. |
| Hardcoded paths? | ⚠️ | `run_memory_layout_test.cpp:78` hardcodes `../../weight-export/character_generator.bin` (works from build dir, fails from repo root). Not a CI blocker (ctest sets the right cwd), but fragile. |
| Test coverage? | ✅ | 460 ctests across unit, parity, differential, blackbox. |
| Stale TODOs? | ⚠️ | 4 remain: `model_compiler_to_C.py:524`, `model_compiler_interactive.py:151`, `test_simple_layer.s:50`, `test_neural_vs_static_comparison.py:56`. All minor. |
| Stale model metadata? | ⚠️ | `router_tab_switch.json` description still says "hidden=4" — should be 16. Does not affect paper or runtime. |

**Rating:** 7.5/10 — Robust, well-tested. 3 minor code-cleanliness items (hardcoded path, 4 TODOs, stale metadata) are non-blocking for submission.

---

## LLM/AI Use in Academic Writing

| Question | Status | Evidence |
|----------|--------|----------|
| AI use disclosed? | ✅ | "AI Use Disclosure" section (`ase2026.md:1025-1034`). Tools named. |
| Disclosure specific? | ⚠️ | Names tools and purpose but does not list iterations or affected sections per `AUDIT_GUIDE.md` §10 recommendation. |
| Claims verified? | ✅ | All 6 data-integrity fixes were driven by errors found during AI-audit cross-checking. The verification loop is working. |
| AI red flags? | ⚠️ | Overuse of bold emphasis and "corporate" phrasing in abstract/intro/OS-taxonomy sections. Otherwise specific and technically grounded. |

**Rating:** 7/10 — Disclosure is present and now names tools. The bold-heavy prose remains a stylistic red flag. The verification loop is working (6 errors found and fixed during audit).

---

## Summary

| Dimension | Rating | Key Finding |
|-----------|--------|-------------|
| Research Quality | 8/10 | Genuinely novel; OS rhetoric slightly overstated. |
| Problem Definition | 8.5/10 | Clear, explicit, traceable. |
| Implementation | 9/10 | 460/460 tests pass; dual backend works. |
| Documentation | 8/10 | Strong; prior self-audit has been revised each round. |
| Paper Quality | 8/10 | All 6 data-integrity issues fixed. No wrong numbers remain. |
| References | 8.5/10 | All verified; [13] fixed. |
| Code Quality | 7.5/10 | Robust; 3 minor cleanliness items open. |
| LLM/AI Integrity | 7/10 | Disclosure present; verification loop working; prose style signals AI assistance. |
| **Overall** | **8.0/10** | The 6 critical data-fixes resolved the major concerns from the prior audit. What remains are prose style, minor code cleanliness, and the inherent gap between the OS-replacement rhetoric and what a 162-line inference loop demonstrates. |

---

## Remaining Open Items

### Paper (non-blocking)
- Toning down OS-replacement framing if reviewer feedback suggests it
- Reducing bold-emphasis density

### Code (non-blocking for submission)
- `run_memory_layout_test.cpp:78` — hardcoded relative path (test passes under ctest, fails from repo root)
- 4 stale TODOs in Python/source files
- `router_tab_switch.json` metadata "hidden=4" → 16

---

## Next Audit

- **Before publication:** Re-run `ctest` and re-derive every number in every table from its cited JSON.
- **After major changes:** Re-run the full suite and update this audit.
