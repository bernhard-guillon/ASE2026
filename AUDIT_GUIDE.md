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
- Do references actually exist (not hallucinated)?
- Do reference details (authors, titles, years, venues) match reality?
- Are non-peer-reviewed sources flagged?

**How to check:**
- Verify each claim has a citation
- Check that references are relevant (not just filler)
- Verify IEEE citation format (see IEEE Format Rules below)
- Check that references are recent (last 5 years for most)
- Verify all references appear in the text
- **For each reference, search online to confirm it exists**
- **Verify author names, titles, years, and venues match the actual publication**
- **Flag any reference that cannot be found online as potentially hallucinated**

**Reference Verification Rules (mandatory for every audit):**

1. **Existence check**: Every reference must be verifiable online (Google Scholar, arXiv, IEEE Xplore, ACM DL, GitHub). If a reference cannot be found, mark it as `⚠️ UNVERIFIED` and investigate.
2. **Author verification**: Author names in the paper must match the actual publication. Initials vs full names, ordering, and "et al." usage must be correct.
3. **Title verification**: The reference title must match the actual publication title exactly (or be a faithful abbreviation).
4. **Year verification**: The publication year must match. arXiv preprint year ≠ conference/journal publication year — use the actual publication year.
5. **Venue verification**: The publication venue (journal, conference, workshop) must be correct. "arXiv" is not a venue — provide the actual venue if published.
6. **DOI verification**: If a DOI is claimed, it must resolve. If no DOI exists, do not fabricate one.
7. **Internal references**: References to repository files (e.g., `[5]`, `[6]`, `[7]`) must point to files that actually exist in the repo.
8. **Non-peer-reviewed flag**: GitHub repos, blog posts, and preprints without peer review should be flagged. They are not invalid but should be noted.

**IEEE Format Rules for References:**

IEEE references follow this structure:
```
[A] Author1, Author2, and Author3, "Title of paper," *Journal/Conference Name*, vol. X, no. Y, pp. N–M, Month Year. [Online]. Available: URL
```

Key rules:
- Authors: Last name + initials (e.g., "A. B. Smith"), "and" before last author
- Title: In quotation marks, sentence case
- Journal/Conference: In italics, abbreviated where standard
- Volume/Issue/Pages: Included when available
- DOI: Included when available (format: `doi: 10.XXXX/XXXXXXX`)
- URLs: Only for online-only sources; include access date if content may change
- Preprints: Cite as "arXiv:XXXX.XXXXX" with the actual submission year
- GitHub repos: Cite with repository URL, version/tag, and access date

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
- [ ] **Every reference verified to exist online (not hallucinated)**
- [ ] **Author names match actual publications**
- [ ] **Publication years match actual publications**
- [ ] **Venue/journal names are correct**
- [ ] **IEEE citation format followed for all references**
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
