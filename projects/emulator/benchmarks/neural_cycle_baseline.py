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
from typing import Dict, Iterable, List


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


def parse_variants(spec: str) -> List[str]:
    variants = [v.strip() for v in spec.split(",") if v.strip()]
    if not variants:
        raise RuntimeError("Variant list resolved to empty set")
    return variants


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


def summarize(values: Iterable[float]) -> Dict[str, float]:
    seq = list(values)
    if not seq:
        raise ValueError("Cannot summarize empty sequence")
    return {
        "min": min(seq),
        "avg": statistics.mean(seq),
        "max": max(seq),
    }


def get_variant_catalog(backend: str) -> Dict[str, BinaryConfig]:
    if backend == "cpp":
        return {
            "x7b-base": BinaryConfig("x7b-base", Path("neural-op-enhance.elf"), 20_000, [1_000, 1_500, 2_000, 3_000, 5_000, 10_000, 20_000]),
            "x7b-4lane": BinaryConfig("x7b-4lane", Path("neural-op-enhance4.elf"), 20_000, [500, 750, 1_000, 1_250, 1_500, 2_000, 3_000, 5_000, 10_000, 20_000]),
            "x7b-8lane": BinaryConfig("x7b-8lane", Path("neural-op-enhance8.elf"), 20_000, [500, 750, 1_000, 1_250, 1_500, 2_000, 3_000, 5_000, 10_000, 20_000]),
            "x7b-8lane-pmac": BinaryConfig("x7b-8lane-pmac", Path("neural-op-enhance8pmac.elf"), 20_000, [500, 750, 1_000, 1_250, 1_500, 2_000, 3_000, 5_000, 10_000, 20_000]),
        }
    if backend == "verilator":
        return {
            "x7b-base": BinaryConfig("x7b-base", Path("neural-op-enhance.elf"), 5_000_000, [250_000, 500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]),
            "x7b-4lane": BinaryConfig("x7b-4lane", Path("neural-op-enhance4.elf"), 5_000_000, [150_000, 200_000, 250_000, 300_000, 400_000, 500_000, 600_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]),
            "x7b-8lane": BinaryConfig("x7b-8lane", Path("neural-op-enhance8.elf"), 5_000_000, [150_000, 200_000, 250_000, 300_000, 400_000, 500_000, 600_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]),
            "x7b-8lane-pmac": BinaryConfig("x7b-8lane-pmac", Path("neural-op-enhance8pmac.elf"), 5_000_000, [100_000, 150_000, 200_000, 250_000, 300_000, 400_000, 500_000, 600_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]),
        }
    raise RuntimeError(f"Unsupported backend: {backend}")


def run_backend(
    backend: str,
    runner: Path,
    chars: List[int],
    baseline_cfg: BinaryConfig,
    optimized_cfg: BinaryConfig,
    variant_cfgs: List[BinaryConfig],
    timeout_s: int,
) -> Dict:
    baseline_cycles: List[int] = []
    optimized_cycles: List[int] = []
    variant_cycles: Dict[str, List[int]] = {cfg.name: [] for cfg in variant_cfgs}
    variant_base_speedups: Dict[str, List[float]] = {cfg.name: [] for cfg in variant_cfgs}
    variant_opt_speedups: Dict[str, List[float]] = {cfg.name: [] for cfg in variant_cfgs}
    lane_scaling_values: List[float] = []
    lane_efficiency_values: List[float] = []
    per_char = []

    for char_code in chars:
        base = first_match_cycle(runner, baseline_cfg, char_code, timeout_s)
        opt = first_match_cycle(runner, optimized_cfg, char_code, timeout_s)
        base_vs_opt = base / opt

        row = {
            "char_code": char_code,
            "char": chr(char_code) if 32 <= char_code <= 126 else f"\\x{char_code:02x}",
            "baseline_cycles": base,
            "optimized_cycles": opt,
            "speedup_baseline_vs_x77": base_vs_opt,
            "variants": {},
        }

        for cfg in variant_cfgs:
            cyc = first_match_cycle(runner, cfg, char_code, timeout_s)
            base_speedup = base / cyc
            x77_speedup = opt / cyc
            row["variants"][cfg.name] = {
                "cycles": cyc,
                "speedup_vs_baseline": base_speedup,
                "speedup_vs_x77": x77_speedup,
            }
            variant_cycles[cfg.name].append(cyc)
            variant_base_speedups[cfg.name].append(base_speedup)
            variant_opt_speedups[cfg.name].append(x77_speedup)

        if "x7b-4lane" in row["variants"] and "x7b-8lane" in row["variants"]:
            lane4 = row["variants"]["x7b-4lane"]["cycles"]
            lane8 = row["variants"]["x7b-8lane"]["cycles"]
            scaling = lane4 / lane8
            efficiency = scaling / 2.0
            row["lane4_to_lane8_scaling"] = scaling
            row["lane4_to_lane8_efficiency_vs_ideal2x"] = efficiency
            lane_scaling_values.append(scaling)
            lane_efficiency_values.append(efficiency)

        baseline_cycles.append(base)
        optimized_cycles.append(opt)
        per_char.append(row)

    report = {
        "backend": backend,
        "runner": str(runner),
        "baseline": {
            "elf": str(baseline_cfg.elf),
            "reference_cycles": baseline_cfg.reference_cycles,
            "threshold_cycles": baseline_cfg.threshold_cycles,
            "summary": summarize(baseline_cycles),
        },
        "optimized_x77": {
            "elf": str(optimized_cfg.elf),
            "reference_cycles": optimized_cfg.reference_cycles,
            "threshold_cycles": optimized_cfg.threshold_cycles,
            "summary": summarize(optimized_cycles),
        },
        "speedup_baseline_vs_x77_summary": summarize([row["speedup_baseline_vs_x77"] for row in per_char]),
        "variants": {},
        "per_char": per_char,
    }

    for cfg in variant_cfgs:
        report["variants"][cfg.name] = {
            "elf": str(cfg.elf),
            "reference_cycles": cfg.reference_cycles,
            "threshold_cycles": cfg.threshold_cycles,
            "summary": summarize(variant_cycles[cfg.name]),
            "speedup_vs_baseline_summary": summarize(variant_base_speedups[cfg.name]),
            "speedup_vs_x77_summary": summarize(variant_opt_speedups[cfg.name]),
        }

    if lane_scaling_values:
        report["lane4_to_lane8_scaling_summary"] = summarize(lane_scaling_values)
        report["lane4_to_lane8_efficiency_vs_ideal2x_summary"] = summarize(lane_efficiency_values)

    return report


def require_file(path: Path, kind: str) -> None:
    if not path.exists():
        raise RuntimeError(f"Missing {kind}: {path}")


def resolve_backend_configs(build_dir: Path, backend: str, variant_names: List[str]):
    if backend == "cpp":
        baseline_cfg = BinaryConfig("baseline", build_dir / "neural.elf", 5_000_000, [2_000_000, 2_500_000, 3_000_000, 4_000_000])
        optimized_cfg = BinaryConfig("x77", build_dir / "neural-ai-opsx77.elf", 20_000, [2_000, 5_000, 10_000, 20_000])
    elif backend == "verilator":
        baseline_cfg = BinaryConfig("baseline", build_dir / "neural.elf", 5_000_000, [2_000_000, 3_000_000, 4_000_000, 5_000_000])
        optimized_cfg = BinaryConfig("x77", build_dir / "neural-ai-opsx77.elf", 5_000_000, [1_000_000, 2_000_000, 3_000_000, 4_000_000])
    else:
        raise RuntimeError(f"Unsupported backend: {backend}")

    catalog = get_variant_catalog(backend)
    variant_cfgs = []
    for name in variant_names:
        if name not in catalog:
            raise RuntimeError(f"Unsupported variant '{name}' for backend {backend}. Supported: {sorted(catalog.keys())}")
        cfg = catalog[name]
        variant_cfgs.append(BinaryConfig(cfg.name, build_dir / cfg.elf, cfg.reference_cycles, cfg.threshold_cycles))

    return baseline_cfg, optimized_cfg, variant_cfgs


def main() -> int:
    parser = argparse.ArgumentParser(description="Neural cycle baseline/hotspot benchmark")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--charset", default="A-Z0-9", help="Chars/ranges, e.g. A-Z0-9")
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--backends",
        default="cpp,verilator",
        help="Comma-separated backends to run: cpp,verilator",
    )
    parser.add_argument(
        "--variants",
        default="x7b-4lane,x7b-8lane",
        help="Comma-separated x7B variants: x7b-base,x7b-4lane,x7b-8lane,x7b-8lane-pmac",
    )
    parser.add_argument(
        "--with-enhanced",
        action="store_true",
        help="Backward-compatible alias: include x7b-base in variant set.",
    )
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    emulator_dir = repo / "projects" / "emulator"
    build_dir = emulator_dir / "build"
    model_json = repo / "projects" / "weight-export" / "character_generator.json"

    require_file(model_json, "model json")

    chars = parse_charset(args.charset)
    requested_backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    if not requested_backends:
        raise RuntimeError("No backends selected")

    variant_names = parse_variants(args.variants)
    if args.with_enhanced and "x7b-base" not in variant_names:
        variant_names.append("x7b-base")

    backend_results = []
    for backend in requested_backends:
        runner = build_dir / ("emulator_runner" if backend == "cpp" else "verilator_runner")
        require_file(runner, f"{backend} runner")

        baseline_cfg, optimized_cfg, variant_cfgs = resolve_backend_configs(build_dir, backend, variant_names)
        require_file(baseline_cfg.elf, "baseline elf")
        require_file(optimized_cfg.elf, "x77 optimized elf")
        for cfg in variant_cfgs:
            require_file(cfg.elf, f"variant elf ({cfg.name})")

        backend_results.append(
            run_backend(
                backend,
                runner,
                chars,
                baseline_cfg,
                optimized_cfg,
                variant_cfgs,
                args.timeout_s,
            )
        )

    report = {
        "charset": args.charset,
        "chars_tested": chars,
        "variant_order": variant_names,
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
