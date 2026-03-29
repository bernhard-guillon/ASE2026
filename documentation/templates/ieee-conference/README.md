# IEEE Conference Template Assets

This directory vendors upstream template assets used to build `documentation/ase2026.pdf` in IEEE conference format.

## Ownership and source

- `IEEEtran.cls` and `bare_conf.tex` are from the IEEEtran package.
- Upstream source: <https://www.ctan.org/pkg/ieeetran>
- Mirror used in this repository setup:
  - <https://mirrors.ctan.org/macros/latex/contrib/IEEEtran/IEEEtran.cls>
  - <https://mirrors.ctan.org/macros/latex/contrib/IEEEtran/bare_conf.tex>

## License

These files are distributed under the LaTeX Project Public License (LPPL), as documented in the file headers and the upstream package.

## Local policy

- Keep upstream attribution and copyright notices intact.
- If modified locally, mark files clearly as modified and preserve original credits.

## Repository-specific template

- `ieee-paper.latex` is a repository-local Pandoc template that targets IEEE conference structure while consuming Markdown metadata from `documentation/ase2026.md`.
- This local file is not an upstream IEEE file; it is maintained in this repository.
