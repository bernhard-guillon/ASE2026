#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def normalize_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""

    if stripped.startswith("."):
        return stripped

    if stripped.endswith(":"):
        return stripped

    line = re.sub(r"\bjr\s+(\w+)\b", r"jalr x0, 0(\1)", stripped)
    line = re.sub(r"\bret\b", "jalr x0, 0(ra)", line)
    line = re.sub(r"\bmv\s+(\w+),\s*(\w+)\b", r"addi \1, \2, 0", line)
    line = re.sub(r"\bj\s+([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"jal x0, \1", line)
    line = re.sub(r"\blla\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"la \1, \2", line)
    line = re.sub(r"\bfgt\.s\s+(\w+),\s*(\w+),\s*(\w+)\b", r"flt.s \1, \3, \2", line)
    line = re.sub(r"^\s*nop\s*$", "addi x0, x0, 0", line)
    line = re.sub(r"\bli\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"la \1, \2", line)
    line = re.sub(r"\bble\s+(\w+),\s*(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"bge \2, \1, \3", line)
    line = re.sub(r"\bbgt\s+(\w+),\s*(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"blt \2, \1, \3", line)
    line = re.sub(r"\bbgez\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"bge \1, x0, \2", line)
    line = re.sub(r"\bblez\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"bge x0, \1, \2", line)
    line = re.sub(r"\bbgtz\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"blt x0, \1, \2", line)
    line = re.sub(r"\bbltz\s+(\w+),\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\b", r"blt \1, x0, \2", line)
    line = re.sub(r"\bseqz\s+(\w+),\s*(\w+)\b", r"sltiu \1, \2, 1", line)
    line = re.sub(r"\bsnez\s+(\w+),\s*(\w+)\b", r"sltu \1, x0, \2", line)
    line = re.sub(r"\bsltz\s+(\w+),\s*(\w+)\b", r"slt \1, \2, x0", line)
    line = re.sub(r"\bsgtz\s+(\w+),\s*(\w+)\b", r"slt \1, x0, \2", line)

    return line


def should_drop_directive(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("."):
        return False
    keep_prefixes = (
        ".section",
        ".text",
        ".data",
        ".rodata",
        ".bss",
        ".align",
        ".globl",
        ".string",
        ".ascii",
        ".asciz",
        ".byte",
        ".half",
        ".word",
    )
    return not stripped.startswith(keep_prefixes)


def normalize(input_path: Path, output_path: Path) -> None:
    out_lines = []
    for raw in input_path.read_text().splitlines():
        if "#" in raw:
            raw = raw.split("#", 1)[0]
        raw = raw.rstrip()
        if not raw.strip():
            continue

        # GCC local labels (e.g. .L2, .LC0) are parsed as directives by rv32as.
        # Rewrite them to regular identifiers so label collection/resolution works.
        raw = re.sub(r"(?<![A-Za-z0-9_])\.L([A-Za-z0-9_.$]*)", r"L\1", raw)

        stripped = raw.strip()
        if stripped.endswith(":"):
            out_lines.append(normalize_line(raw))
            continue

        call_match = re.match(r"^\s*call\s+([A-Za-z_.$][A-Za-z0-9_.$]*)\s*$", stripped)
        if call_match:
            sym = call_match.group(1)
            out_lines.append(f"la t0, {sym}")
            out_lines.append("jalr ra, 0(t0)")
            continue

        # GNU fmv.s (register move alias) is normalized to a two-instruction sequence
        # using already-supported fmv.x.w / fmv.w.x.
        fmv_s_match = re.match(r"^\s*fmv\.s\s+(\w+),\s*(\w+)\s*$", stripped)
        if fmv_s_match:
            dst = fmv_s_match.group(1)
            src = fmv_s_match.group(2)
            out_lines.append(f"fmv.x.w t6, {src}")
            out_lines.append(f"fmv.w.x {dst}, t6")
            continue

        if should_drop_directive(raw):
            continue

        norm = normalize_line(raw)
        if not norm:
            continue
        out_lines.append(norm)

    output_path.write_text("\n".join(out_lines) + "\n")


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.s> <output.s>", file=sys.stderr)
        return 1

    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    normalize(inp, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
