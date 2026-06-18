# How to Audit This Project

This guide derives the audit framework from AUDIT.md.
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
- Is the architecture documented? (COMBINING.md, combined-mlp.md)
- Are code conventions followed? (no comments unless asked, existing patterns)
- Is documentation machine-readable? (clear sections, consistent formatting, structured data)

**How to check:**
- Read `README.md` — does it match actual commands?
- Read `projects/emulator/AGENTS.md` — are build/test commands correct?
- Read `projects/emulator/COMBINING.md` — does it match actual implementation?
- Read `projects/emulator/BUILD_DIRECTORY.md` — is the build directory correct?
- Check if an AI agent can parse sections without ambiguity

**Known issues (as of latest commit):**
- `AUDIT.md` — evaluation date says "2024" (should be 2026)

### 4. Paper Quality

**Questions to answer:**
- Does the abstract clearly state the problem, approach, and results?
- Does the introduction motivate the research and state contributions?
- Is related work properly positioned against existing literature?
- Is the methodology clearly described?
- Are results properly presented and analyzed?
- Does the conclusion summarize contributions and future work?

**Paper structure checklist:**
- [ ] Abstract: Problem, approach, results (all present)
- [ ] Introduction: Motivation, contributions, paper organization
- [ ] Related Work: Proper positioning, not just a list
- [ ] Methodology: Clear description of approach
- [ ] Evaluation: Properly presented results with analysis
- [ ] Conclusion: Summary, limitations, future work

**How to check:**
- Read `documentation/ase2026.md` — paper source
- Read `documentation/ase2026.pdf` — compiled paper
- Check IEEE format compliance
- Verify all claims are properly cited

### 5. Paper Writing Quality

**Questions to answer:**
- Is the writing clear and concise?
- Are there grammatical errors?
- Is terminology consistent throughout?
- Does it follow IEEE format requirements?
- Are acronyms properly defined?

**How to check:**
- Read the paper carefully for clarity
- Check for grammatical errors
- Verify terminology consistency
- Check IEEE format compliance (columns, fonts, margins)
- Verify all acronyms are defined on first use

### 6. Paper Figures and Diagrams

**Questions to answer:**
- Are figures clear and readable?
- Do figures support the text?
- Are captions descriptive and complete?
- Are figures properly referenced in the text?
- Do figures have proper resolution?

**How to check:**
- View all figures in the paper
- Verify each figure is referenced in the text
- Check that captions explain the figure content
- Verify figures are properly labeled (Figure 1, Figure 2, etc.)

### 7. Paper References

**Questions to answer:**
- Are all claims properly cited?
- Are references relevant to the work?
- Are references properly formatted?
- Is the reference list complete?
- Are recent references included?

**How to check:**
- Verify each claim has a citation
- Check that references are relevant (not just filler)
- Verify IEEE citation format
- Check that references are recent (last 5 years for most)
- Verify all references appear in the text

### 8. Code Quality

**Questions to answer:**
- Is error handling robust? (check NeuralOps.cpp, Emulator.cpp)
- Are there hardcoded paths that should be configurable?
- Is test coverage sufficient? (check edge cases)
- Are there any TODO/FIXME/HACK comments?

**How to check:**
```bash
# Find TODO/FIXME/HACK
grep -r "TODO\|FIXME\|HACK" projects/emulator/ projects/emulator/hdl/

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
- [ ] Documentation is machine-readable

### Paper
- [ ] Abstract clearly states problem, approach, results
- [ ] Introduction motivates research and states contributions
- [ ] Related work properly positions the work
- [ ] Methodology clearly described
- [ ] Results properly presented and analyzed
- [ ] Conclusion summarizes contributions and future work
- [ ] All claims properly cited
- [ ] References are relevant and complete
- [ ] Figures are clear and properly referenced
- [ ] IEEE format requirements met

### Code Quality
- [ ] Error handling is robust
- [ ] No hardcoded paths
- [ ] Test coverage is sufficient
- [ ] No stale TODO/FIXME comments

## Audit Workflow

1. **Read the docs** — Start with README.md, AGENTS.md, COMBINING.md
2. **Build and test** — Run the build and test commands above
3. **Inspect code** — Check key files (NeuralOps.cpp, main.rs, CMakeLists.txt)
4. **Read the paper** — Read `documentation/ase2026.md` carefully
5. **Verify claims** — Check that documentation matches reality
6. **Fill checklist** — Use the checklist above
7. **Document findings** — Update AUDIT.md with current ratings

## Re-audit Schedule

- **After major changes**: Re-run full test suite, verify documentation
- **Before publication**: Full audit with checklist
- **Quarterly**: Quick check of build/test/docs

## AI Agent Audit Notes

This audit is designed to be read by AI agents (e.g., Claude). When auditing:

1. **Be specific** — Include file paths and line numbers for findings
2. **Provide evidence** — Reference specific files, tests, or code sections
3. **Use structured format** — Tables and bullet points are preferred
4. **Include verification steps** — Show how to verify each finding
5. **Rate consistently** — Use the same scale across all dimensions
