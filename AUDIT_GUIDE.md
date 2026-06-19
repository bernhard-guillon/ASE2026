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

### 2. Problem Definition and Research Question

**Questions to answer:**
- Is the problem clearly defined and scoped?
- Is the research question explicitly stated in the paper?
- Is the research question specific, measurable, and answerable?
- Does the paper's methodology directly address the research question?
- Do the evaluation results answer the research question?
- Does the conclusion explicitly state how the problem was addressed?
- Is there a clear line from problem → research question → methodology → evaluation → conclusion?
- Does the paper avoid answering a different question than the one posed?

**How to check:**
- Read the introduction — is the problem motivated and the research question stated?
- Read the methodology — does it describe how the research question is investigated?
- Read the evaluation — do the results directly answer the research question?
- Read the conclusion — does it explicitly state how the problem was addressed?
- Check consistency: the same research question must appear (or be implied) in the abstract, introduction, evaluation, and conclusion.

**Checklist (mandatory):**
- [ ] **Problem explicitly stated** in the introduction
- [ ] **Research question explicitly stated** (not just implied)
- [ ] **Methodology addresses** the research question
- [ ] **Evaluation results answer** the research question
- [ ] **Conclusion addresses** the problem and research question
- [ ] **Traceable thread**: problem → RQ → methodology → evaluation → conclusion
- [ ] **No scope drift**: the paper does not answer a different question

### 3. Implementation Quality

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

### 4. Documentation Quality

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
- ~~`AUDIT.md` — evaluation date says "2024" (should be 2026)~~ ✅ Fixed — now reads "2026-06-19".

### 5. Paper Quality

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

### 6. Paper Writing Quality

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

### 7. Paper Figures and Diagrams

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

### 8. Paper References

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

### 9. Code Quality

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

### 10. LLM/AI Use in Academic Writing

This dimension addresses integrity requirements specific to AI-assisted academic papers, derived from university guidelines (FIU, DCU, NC State, University of Rochester, Aalto University), publisher policies (Elsevier, IEEE, arXiv 2026 ban), and research on AI-generated content detection (Lesniewski 2026, Paper Checker 2026, PMC 2026).

**Questions to answer:**
- Is AI/LLM use disclosed in the paper?
- Is the disclosure specific (tool, version, purpose, sections affected)?
- Are AI-generated claims verified against primary sources?
- Are AI-generated citations independently verified?
- Can the author demonstrate their individual contribution?
- Does the paper avoid AI red flags (generic language, phantom citations, uniform structure)?

**Disclosure Requirements (based on university guidelines):**

The paper must include an AI Use Disclosure statement. Required elements:
1. **Tool identification**: Name and version/model of the AI tool(s) used
2. **Purpose and scope**: What the tool was used for (writing, coding, data analysis, figure generation, literature review)
3. **Affected sections**: Which parts of the paper involved AI assistance
4. **Verification process**: How the author reviewed and verified AI output
5. **Iterative refinement**: Number of iterations and how output was modified

Recommended placement: Acknowledgments section or a dedicated "AI Use Declaration" section.

Example disclosure:
> "The author used Claude (Anthropic, 2026) for code refactoring and draft editing.
> All technical claims, benchmarks, and references were independently verified by the author.
> The author reviewed and modified all AI-generated output for accuracy and originality."

**Red Flags for AI-Generated Content (from detection research):**

| Category | Red Flag | What to Check |
|----------|----------|---------------|
| **Tone** | Unusually consistent, neutral, "corporate" tone throughout | Does the writing have natural variation? |
| **Structure** | Overly uniform paragraph structure, predictable transitions | Are "However," "Moreover," "In conclusion" overused? |
| **Content** | Generic/vague statements without specific examples or data | Does the paper provide concrete details from the project? |
| **Citations** | Phantom references that look real but don't exist | Were all references verified online? (See dimension 7) |
| **Facts** | Confidently incorrect or outdated claims | Can all technical claims be verified in the codebase? |
| **Logic** | Contradictory points or circular reasoning | Is the argumentation internally consistent? |
| **Voice** | Lack of personal perspective, anecdotes, or lived experience | Does the author's unique voice come through? |
| **Perfection** | Clean grammar with almost no typos or idiosyncrasies | Some natural imperfection is expected in human writing |

**Verification Protocol (mandatory for every audit):**

1. **Claim verification**: Every major technical claim must be traceable to:
   - Source code in the repository
   - Benchmark data in `documentation/collected-data/`
   - Test results from the build system
   If a claim cannot be traced, flag it as unverified.

2. **Citation verification**: Every reference must be independently verified (see dimension 7). AI tools are known to hallucinate citations — fabricating non-existent papers, authors, DOIs, or mixing up real papers (arXiv 2026 ban, NeurIPS 2025 findings).

3. **Originality check**: Compare the paper's writing style with:
   - The author's previous commits and documentation
   - Natural imperfections (minor typos, personal phrasing, field-specific jargon)
   - Depth of domain knowledge (AI tends to be superficial)

4. **Process documentation**: The author should be able to produce:
   - Earlier drafts or version history
   - Notes, outlines, or research materials
   - Explanation of how AI was used (if at all)

5. **Self-consistency check**: The paper must not contain:
   - Contradictions between sections
   - Claims that contradict the codebase
   - Figures or tables that don't match the text

**Acceptable vs. Unacceptable AI Use (from university guidelines):**

| Generally Acceptable | Generally Not Acceptable |
|---------------------|-------------------------|
| Proofreading and grammar correction | Generating entire sections without substantial revision |
| Suggesting alternative phrasings | Creating research ideas, hypotheses, or conclusions |
| Code refactoring with human review | Generating citations without verification |
| Summarizing literature found by the author | Replacing the author's critical analysis |
| Formatting and structuring existing content | Generating data or experimental results |
| Language translation with human verification | Presenting AI output as entirely human-written |

**Academic Integrity Principles (from PMC/Aalto guidelines):**

1. **Human vetting and guaranteeing**: The author must review and take responsibility for all content
2. **Substantial human contribution**: The primary ideas, insights, and analyses must be the author's own
3. **Acknowledgement and transparency**: AI use must be disclosed clearly and explicitly
4. **Reproducibility**: The research process must be documented and reproducible
5. **Accountability**: The author is accountable for all output, including AI-assisted content

## Audit Checklist

Use this checklist when auditing the project:

### Research
- [ ] Novel contribution identified and documented
- [ ] Related work comparison exists
- [ ] Measurable results (cycle counts, accuracy, speedup)
- [ ] Impact potential articulated

### Problem Definition
- [ ] **Problem explicitly stated** in the introduction
- [ ] **Research question explicitly stated** in the paper
- [ ] **Methodology addresses** the research question
- [ ] **Evaluation results answer** the research question
- [ ] **Conclusion addresses** both problem and research question
- [ ] **Traceable thread**: problem → RQ → methodology → evaluation → conclusion
- [ ] **No scope drift**: paper does not answer a different question

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

### LLM/AI Use in Academic Writing
- [ ] **AI use is disclosed** (tool, version, purpose, affected sections)
- [ ] **Disclosure is in the paper** (Acknowledgments or dedicated section)
- [ ] **All AI-generated claims verified** against source code and data
- [ ] **All references independently verified** (not hallucinated)
- [ ] **Author can demonstrate individual contribution** (drafts, notes, version history)
- [ ] **No AI red flags** (generic language, phantom citations, uniform structure)
- [ ] **Writing shows natural human variation** (personal voice, specific details, minor imperfections)
- [ ] **Technical claims traceable** to codebase, benchmarks, or test results
- [ ] **Paper is internally consistent** (no contradictions between sections)

## Audit Workflow

1. **Read the docs** — Start with README.md, AGENTS.md, COMBINING.md
2. **Build and test** — Run the build and test commands above
3. **Inspect code** — Check key files (NeuralOps.cpp, main.rs, CMakeLists.txt)
4. **Read the paper** — Read `documentation/ase2026.md` carefully
5. **Verify problem definition** — Identify the stated problem and research question; trace their thread through abstract → introduction → methodology → evaluation → conclusion
6. **Verify claims** — Check that documentation matches reality
7. **Verify references** — Search each reference online, confirm authors/titles/venues
8. **Check AI/LLM integrity** — Verify disclosure, check for red flags, trace claims to codebase
9. **Fill checklist** — Use the checklist above
10. **Document findings** — Update AUDIT.md with current ratings

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
