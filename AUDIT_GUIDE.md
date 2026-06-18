# How to Audit This Project

This guide derives the audit framework from AUDIT.md and new-audit.md.
Use it to evaluate the project's current state and identify improvements.

## Audit Dimensions

### 1. Research Quality

**Questions to answer:**
- What is the novel contribution? (descriptor-based neural ISA, block-diagonal composition, dual-backend validation)
- How does it compare to related work? (nCPU, MARVEL, RV-SCNN, NVDLA)
- Is there measurable evidence of correctness? (deterministic tests, cycle counts, accuracy)
- What is the impact potential? (edge AI, tiny RISC-V cores)

**How to check:**
- Read `projects/emulator/AGENTS.md` for project overview
- Read `projects/emulator/COMBINING.md` for composition methodology
- Read `projects/emulator/block-diagonal-composition.md` for related work
- Run `ctest --test-dir projects/emulator/build -R "verilator" --output-on-failure` to verify dual-backend validation

### 2. Implementation Quality

**Questions to answer:**
- Does the end-to-end pipeline work? (train → export → compile → assemble → run)
- Are both backends (emulator + verilator) functional?
- Is there CI/CD? (GitHub Actions workflow)
- Are there tests for critical paths? (unit tests, blackbox tests, differential tests)

**How to check:**
```bash
# Full build
cmake -S projects/emulator -B projects/emulator/build
cmake --build projects/emulator/build -j$(nproc)

# Unit tests (~200 tests)
./projects/emulator/build/test_*

# Blackbox tests
ctest --test-dir projects/emulator/build --output-on-failure

# Verilator differential tests
ctest --test-dir projects/emulator/build -R "verilator" --output-on-failure
```

**Files to inspect:**
- `.github/workflows/emulator-tests.yml` — CI configuration
- `projects/emulator/CMakeLists.txt` — build targets and test registrations
- `projects/emulator/utest/` — GoogleTest unit tests
- `projects/emulator/blackbox_tests/` — integration tests

### 3. Documentation Quality

**Questions to answer:**
- Is there a clear project overview? (README.md, AGENTS.md)
- Are build instructions accurate? (BUILD_DIRECTORY.md, AGENTS.md)
- Is the architecture documented? (architecture.md, COMBINING.md, combined-mlp.md)
- Are code conventions followed? (no comments unless asked, existing patterns)

**How to check:**
- Read `README.md` — does it match actual commands?
- Read `projects/emulator/AGENTS.md` — are build/test commands correct?
- Read `projects/emulator/COMBINING.md` — does it match actual implementation?
- Read `projects/emulator/BUILD_DIRECTORY.md` — is the build directory correct?

**Known issues (as of latest commit):**
- `architecture.md` — "Current Limitation" claims block-diagonal not implemented (it was)
- `new-audit.md` — wrong path `hdl/cpu.v` → should be `hdl/rtl/cpu.v`
- `AUDIT.md` — evaluation date says "2024" (should be 2026)

### 4. Publication Readiness

**Questions to answer:**
- Is there a paper draft? (`documentation/` directory)
- Are there benchmarks? (`documentation/collected-data/`)
- Is there a comparison with related work? (`block-diagonal-composition.md`)
- What would make it stronger? (see new-audit.md suggestions)

**How to check:**
- Read `documentation/paper/` — paper draft status
- Read `documentation/collected-data/` — benchmark data
- Read `projects/emulator/block-diagonal-composition.md` — related work coverage

### 5. Code Quality

**Questions to answer:**
- Is error handling robust? (check NeuralOps.cpp, Emulator.cpp)
- Are there hardcoded paths that should be configurable?
- Is test coverage sufficient? (check edge cases)
- Are there any TODO/FIXME/HACK comments?

**How to check:**
```bash
# Find TODO/FIXME/HACK
grep -r "TODO\|FIXME\|HACK" projects/emulator/src/ projects/emulator/hdl/

# Check test coverage
ctest --test-dir projects/emulator/build --output-on-failure 2>&1 | grep -E "Passed|Failed|Skipped"
```

## Audit Checklist

Use this checklist when auditing the project:

### Research
- [ ] Novel contribution identified and documented
- [ ] Related work comparison exists
- [ ] Measurable results (cycle counts, accuracy, speedup)
- [ ] Impact potential articulated

### Implementation
- [ ] End-to-end pipeline works (train → run)
- [ ] Both backends functional (emulator + verilator)
- [ ] CI/CD configured and passing
- [ ] Unit tests pass
- [ ] Blackbox tests pass
- [ ] Differential tests pass

### Documentation
- [ ] Project overview exists and is accurate
- [ ] Build instructions work
- [ ] Architecture documentation is current
- [ ] Code conventions are followed

### Publication
- [ ] Paper draft exists
- [ ] Benchmarks collected
- [ ] Related work cited
- [ ] Figures and diagrams included

### Code Quality
- [ ] Error handling is robust
- [ ] No hardcoded paths
- [ ] Test coverage is sufficient
- [ ] No stale TODO/FIXME comments

## Audit Workflow

1. **Read the docs** — Start with README.md, AGENTS.md, COMBINING.md
2. **Build and test** — Run the build and test commands above
3. **Inspect code** — Check key files (NeuralOps.cpp, main.rs, CMakeLists.txt)
4. **Verify claims** — Check that documentation matches reality
5. **Fill checklist** — Use the checklist above
6. **Document findings** — Update AUDIT.md with current ratings

## Re-audit Schedule

- **After major changes**: Re-run full test suite, verify documentation
- **Before publication**: Full audit with checklist
- **Quarterly**: Quick check of build/test/docs
