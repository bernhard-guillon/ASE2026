#!/usr/bin/env python3
"""
Baseline cycle threshold benchmark for neural character generation binaries.

This script is intentionally fail-loud:
- Missing binaries/tooling are hard errors.
- Missing framebuffer output is a hard error.
- If no threshold cycle matches the reference framebuffer, the run fails.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
GRID_CHARS = {" ", "#", "█"}


@dataclass
class BinaryConfig:
    name: str
    elf: Path
    reference_cycles: int
    threshold_cycles: List[int]


def parse_charset(spec: str) -> List[int]:
    chars: List[int] = []
    i = 0
    while i < len(spec):
        if i + 2 < len(spec) and spec[i + 1] == "-":
            start = ord(spec[i])
            end = ord(spec[i + 2])
            if end < start:
                raise ValueError(f"Invalid range in charset: {spec[i:i+3]}")
            chars.extend(range(start, end + 1))
            i += 3
        else:
            chars.append(ord(spec[i]))
            i += 1
    if not chars:
        raise ValueError("Charset resolved to empty set")
    return chars


def extract_grid(output: str) -> str:
    clean = ANSI_ESCAPE.sub("", output)
    lines: List[str] = []
    for line in clean.splitlines():
        if len(line) == 20 and all(ch in GRID_CHARS for ch in line):
            lines.append(line.replace("█", "#"))
    if len(lines) < 20:
        raise RuntimeError("Framebuffer grid not found in emulator output")
    return "\n".join(lines[:20])


def run_once(runner: Path, elf: Path, char_code: int, cycles: int, timeout_s: int) -> str:
    result = subprocess.run(
        [
            str(runner),
            str(elf),
            "--char-code",
            str(char_code),
            "--cycles",
            str(cycles),
            "--render-framebuffer",
        ],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Runner failed (code {result.returncode}) for {elf.name} char={char_code} cycles={cycles}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return extract_grid(result.stdout)


def first_match_cycle(
    runner: Path,
    cfg: BinaryConfig,
    char_code: int,
    timeout_s: int,
) -> int:
    reference = run_once(runner, cfg.elf, char_code, cfg.reference_cycles, timeout_s)
    for cycle in cfg.threshold_cycles:
        grid = run_once(runner, cfg.elf, char_code, cycle, timeout_s)
        if grid == reference:
            return cycle
    raise RuntimeError(
        f"No matching threshold found for {cfg.name} char={char_code}. "
        f"Tried: {cfg.threshold_cycles}, reference={cfg.reference_cycles}"
    )


def load_hotspots(model_json: Path) -> Dict:
    with model_json.open("r", encoding="utf-8") as f:
        model = json.load(f)
    layers = model.get("layers", [])
    if not layers:
        raise RuntimeError(f"No layers in model json: {model_json}")
    layer_stats = []
    total_macs = 0
    total_acts = 0
    for idx, layer in enumerate(layers):
        input_size = int(layer["input_size"])
        output_size = int(layer["output_size"])
        macs = input_size * output_size
        acts = output_size if layer.get("activation", "none") != "none" else 0
        layer_stats.append(
            {
                "layer_index": idx,
                "input_size": input_size,
                "output_size": output_size,
                "activation": layer.get("activation", "none"),
                "macs": macs,
                "activations": acts,
            }
        )
        total_macs += macs
        total_acts += acts
    for stat in layer_stats:
        stat["mac_share_percent"] = round((stat["macs"] / total_macs) * 100.0, 3)
    return {
        "total_layers": len(layers),
        "total_macs": total_macs,
        "total_activations": total_acts,
        "layers": layer_stats,
    }


def summarize(values: Iterable[int]) -> Dict[str, float]:
    seq = list(values)
    if not seq:
        raise ValueError("Cannot summarize empty sequence")
    return {
        "min": min(seq),
        "avg": statistics.mean(seq),
        "max": max(seq),
    }


def run_backend(
    backend: str,
    runner: Path,
    chars: List[int],
    baseline_cfg: BinaryConfig,
    optimized_cfg: BinaryConfig,
    enhanced_cfg: Optional[BinaryConfig],
    timeout_s: int,
) -> Dict:
    baseline_cycles = []
    optimized_cycles = []
    enhanced_cycles = []
    per_char = []
    for char_code in chars:
        base = first_match_cycle(runner, baseline_cfg, char_code, timeout_s)
        opt = first_match_cycle(runner, optimized_cfg, char_code, timeout_s)
        speedup = base / opt
        enh = None
        enh_speedup = None
        enh_vs_opt = None
        if enhanced_cfg is not None:
            enh = first_match_cycle(runner, enhanced_cfg, char_code, timeout_s)
            enh_speedup = base / enh
            enh_vs_opt = opt / enh
        baseline_cycles.append(base)
        optimized_cycles.append(opt)
        if enh is not None:
            enhanced_cycles.append(enh)
        per_char.append(
            {
                "char_code": char_code,
                "char": chr(char_code) if 32 <= char_code <= 126 else f"\\x{char_code:02x}",
                "baseline_cycles": base,
                "optimized_cycles": opt,
                "speedup": speedup,
                "enhanced_cycles": enh,
                "enhanced_speedup": enh_speedup,
                "enhanced_vs_optimized_speedup": enh_vs_opt,
            }
        )
    report = {
        "backend": backend,
        "runner": str(runner),
        "baseline": {
            "elf": str(baseline_cfg.elf),
            "reference_cycles": baseline_cfg.reference_cycles,
            "threshold_cycles": baseline_cfg.threshold_cycles,
            "summary": summarize(baseline_cycles),
        },
        "optimized": {
            "elf": str(optimized_cfg.elf),
            "reference_cycles": optimized_cfg.reference_cycles,
            "threshold_cycles": optimized_cfg.threshold_cycles,
            "summary": summarize(optimized_cycles),
        },
        "speedup_summary": summarize([row["speedup"] for row in per_char]),
        "per_char": per_char,
    }
    if enhanced_cfg is not None:
        report["enhanced"] = {
            "elf": str(enhanced_cfg.elf),
            "reference_cycles": enhanced_cfg.reference_cycles,
            "threshold_cycles": enhanced_cfg.threshold_cycles,
            "summary": summarize(enhanced_cycles),
        }
        report["enhanced_speedup_summary"] = summarize(
            [row["enhanced_speedup"] for row in per_char if row["enhanced_speedup"] is not None]
        )
        report["enhanced_vs_optimized_speedup_summary"] = summarize(
            [
                row["enhanced_vs_optimized_speedup"]
                for row in per_char
                if row["enhanced_vs_optimized_speedup"] is not None
            ]
        )
    return report


def require_file(path: Path, kind: str) -> None:
    if not path.exists():
        raise RuntimeError(f"Missing {kind}: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Neural cycle baseline/hotspot benchmark")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--charset", default="AZ09", help="Chars/ranges, e.g. A-Z0-9 or AZ09")
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--backends",
        default="cpp,verilator",
        help="Comma-separated backends to run: cpp,verilator",
    )
    parser.add_argument(
        "--with-enhanced",
        action="store_true",
        help="Also benchmark 0x7B enhanced ELF (neural-op-enhance.elf).",
    )
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    emulator_dir = repo / "projects" / "emulator"
    build_dir = emulator_dir / "build"
    model_json = repo / "projects" / "weight-export" / "character_generator.json"

    require_file(model_json, "model json")

    baseline_elf = build_dir / "neural.elf"
    optimized_elf = build_dir / "neural-ai-opsx77.elf"
    enhanced_elf = build_dir / "neural-op-enhance.elf"
    require_file(baseline_elf, "baseline elf")
    require_file(optimized_elf, "optimized elf")
    if args.with_enhanced:
        require_file(enhanced_elf, "enhanced elf")

    chars = parse_charset(args.charset)
    requested_backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    if not requested_backends:
        raise RuntimeError("No backends selected")

    cpp_cfgs = (
        BinaryConfig("baseline", baseline_elf, 5_000_000, [2_000_000, 2_500_000, 3_000_000, 4_000_000]),
        BinaryConfig("optimized", optimized_elf, 20_000, [2_000, 5_000, 10_000, 20_000]),
    )
    cpp_enhanced_cfg = BinaryConfig(
        "enhanced",
        enhanced_elf,
        20_000,
        [1_000, 1_500, 2_000, 3_000, 5_000, 10_000, 20_000],
    )
    vlt_cfgs = (
        BinaryConfig("baseline", baseline_elf, 5_000_000, [2_000_000, 3_000_000, 4_000_000, 5_000_000]),
        BinaryConfig("optimized", optimized_elf, 5_000_000, [1_000_000, 2_000_000, 3_000_000, 4_000_000]),
    )
    vlt_enhanced_cfg = BinaryConfig(
        "enhanced",
        enhanced_elf,
        5_000_000,
        [250_000, 500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000],
    )

    backend_results = []
    for backend in requested_backends:
        if backend == "cpp":
            runner = build_dir / "emulator_runner"
            require_file(runner, "cpp runner")
            backend_results.append(
                run_backend(
                    backend,
                    runner,
                    chars,
                    cpp_cfgs[0],
                    cpp_cfgs[1],
                    cpp_enhanced_cfg if args.with_enhanced else None,
                    args.timeout_s,
                )
            )
        elif backend == "verilator":
            runner = build_dir / "verilator_runner"
            require_file(runner, "verilator runner")
            backend_results.append(
                run_backend(
                    backend,
                    runner,
                    chars,
                    vlt_cfgs[0],
                    vlt_cfgs[1],
                    vlt_enhanced_cfg if args.with_enhanced else None,
                    args.timeout_s,
                )
            )
        else:
            raise RuntimeError(f"Unsupported backend: {backend}")

    report = {
        "charset": args.charset,
        "chars_tested": chars,
        "hotspots": load_hotspots(model_json),
        "results": backend_results,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(f"Wrote cycle report: {args.output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
