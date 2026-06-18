# Documentation Directory

This directory contains the project paper, presentation, and supporting documentation.

## Paper Pipeline

The paper uses a **Markdown → LaTeX → PDF** pipeline:

1. **Source**: `ase2026.md` (Markdown with YAML frontmatter and embedded LaTeX)
2. **Template**: `templates/ieee-conference/ieee-paper.latex` (Pandoc LaTeX template)
3. **Build**: `ase2026.pdf` (compiled PDF output)

### Build Command

```bash
TEXINPUTS=documentation/templates/ieee-conference//: \
pandoc documentation/ase2026.md \
  --from markdown-smart \
  --lua-filter=documentation/pandoc-filters/ieee_table.lua \
  --pdf-engine=xelatex \
  -V documentclass=IEEEtran \
  -V classoption=conference \
  --template documentation/templates/ieee-conference/ieee-paper.latex \
  -o documentation/ase2026.pdf
```

### Writing the Paper

#### Figures

Use LaTeX figure environments in the Markdown source:

```latex
\begin{figure}[h]
\centering
\small
\begin{tabular}{|l|c|}
\hline
Column 1 & Column 2 \\
\hline
Data & Data \\
\hline
\end{tabular}
\caption{Figure caption.}
\label{fig:label}
\end{figure}
```

**Important**: Use `\begin{figure}[h]` (not `[H]`) for IEEE format. The `[h]` placement is more flexible.

#### Tables

Tables can be written as Markdown tables or LaTeX tables. Markdown tables are converted by the `ieee_table.lua` filter.

#### Code Blocks

Code blocks use `\begin{verbatim}...\end{verbatim}` for inline code in figures, or Markdown fenced code blocks for regular code.

#### Math

Inline math: `$ equation $`
Display math: `$$ equation $$`

### YAML Frontmatter

The paper includes metadata in YAML frontmatter:

```yaml
---
title: "ASE2026 - Neural-driven Computing"
project_title: "Full Paper Title"
authors:
  - name: "Author Name"
    department: "Department"
    university: "University"
    email: "email@example.com"
supervisor: "Supervisor Name"
course: "Course Name"
university: "University Name"
date: "2026-06-18"
abstract: >
  Paper abstract...
keywords:
  - keyword1
  - keyword2
---
```

### File Structure

```
documentation/
├── ase2026.md                    # Paper source (Markdown + LaTeX)
├── ase2026.pdf                   # Compiled PDF (generated)
├── project-log.md                # Project log
├── neural-risc-v-machine.md      # Neural machine reference
├── collected-data/               # Benchmark data (JSON)
├── assets/                       # Images and media
├── pandoc-filters/               # Custom Pandoc filters
│   └── ieee_table.lua           # Table conversion filter
└── templates/                    # LaTeX templates
    └── ieee-conference/
        └── ieee-paper.latex      # Pandoc template
```

## Agent Guidelines

When editing the paper:

1. **Use LaTeX figure environments** for all figures (not ASCII art)
2. **Keep YAML frontmatter updated** with current metadata
3. **Use consistent terminology** across sections
4. **Cite all claims** with numbered references
5. **Test the build** after major changes

## Related Files

- `../AGENTS.md` — Project-wide guidelines
- `../AUDIT.md` — Project audit
- `../AUDIT_GUIDE.md` — How to audit this project
