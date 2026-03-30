#!/usr/bin/env python3
"""
Generate README visual assets for ASE2026.

Outputs:
- documentation/assets/neural-character-generation.gif
- documentation/assets/neural-speedup-progression.gif
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "documentation" / "assets"

CHARS_NPY = ROOT / "projects" / "character-generation" / "pytorch_all_256_chars.npy"
PHASE25_JSON = ROOT / "documentation" / "collected-data" / "phase25-neural-lane-cycle-comparison.json"


def make_character_generation_gif() -> Path:
    data = np.load(CHARS_NPY)
    if data.ndim != 3 or data.shape[1:] != (20, 20):
        raise RuntimeError(f"Unexpected character tensor shape: {data.shape}")

    sequence = "ASE2026  PMAC4  X7B  NEURAL  "
    char_codes = [ord(ch) for ch in sequence if ord(ch) < data.shape[0]]

    frames: list[Image.Image] = []
    for idx, code in enumerate(char_codes):
        glyph = np.clip(data[code], 0.0, 1.0)
        glyph_u8 = (glyph * 255.0).astype(np.uint8)
        glyph_img = Image.fromarray(glyph_u8, mode="L").resize((200, 200), Image.Resampling.NEAREST).convert("RGB")

        canvas = Image.new("RGB", (760, 260), color=(14, 18, 24))
        draw = ImageDraw.Draw(canvas)

        canvas.paste(glyph_img, (24, 30))
        draw.text((250, 40), "Neural Character Generation", fill=(230, 240, 255))
        draw.text((250, 85), f"Frame {idx + 1}/{len(char_codes)}", fill=(170, 185, 205))
        draw.text((250, 125), f"ASCII {code}   Character: {repr(chr(code))}", fill=(210, 220, 235))
        draw.text((250, 170), "Pipeline: one-hot input -> FC layers -> framebuffer glyph", fill=(170, 185, 205))
        draw.text((250, 205), "Model: 255 -> 256 -> 256 -> 400 (20x20)", fill=(170, 185, 205))

        frames.append(canvas)

    out = ASSETS_DIR / "neural-character-generation.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=260,
        loop=0,
        optimize=True,
    )
    return out


def _extract_phase25_verilator_cycles() -> tuple[list[str], list[float]]:
    payload = json.loads(PHASE25_JSON.read_text(encoding="utf-8"))
    rows = payload.get("results", [])
    verilator = next((r for r in rows if r.get("backend") == "verilator"), None)
    if verilator is None:
        raise RuntimeError("Could not find verilator backend in phase25 benchmark JSON")

    labels = ["baseline", "x77", "x7b-8lane", "x7b-8lane-pmac", "x7b-8lane-pmac2", "x7b-8lane-pmac3", "x7b-8lane-pmac4"]
    values = [
        float(verilator["baseline"]["summary"]["avg"]),
        float(verilator["optimized_x77"]["summary"]["avg"]),
        float(verilator["variants"]["x7b-8lane"]["summary"]["avg"]),
        float(verilator["variants"]["x7b-8lane-pmac"]["summary"]["avg"]),
        float(verilator["variants"]["x7b-8lane-pmac2"]["summary"]["avg"]),
        float(verilator["variants"]["x7b-8lane-pmac3"]["summary"]["avg"]),
        float(verilator["variants"]["x7b-8lane-pmac4"]["summary"]["avg"]),
    ]
    return labels, values


def make_speedup_progression_gif() -> Path:
    labels, values = _extract_phase25_verilator_cycles()
    baseline = values[0]

    images: list[Image.Image] = []
    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i in range(2, len(labels) + 1):
            cur_labels = labels[:i]
            cur_values = values[:i]

            fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=120)
            colors = ["#4F81BD"] * (i - 1) + ["#D8572A"]
            bars = ax.bar(cur_labels, cur_values, color=colors)
            ax.set_yscale("log")
            ax.set_ylabel("Cycle threshold (log scale)")
            ax.set_title("Verilator progression: baseline -> PMAC4 (Phase 25)")
            ax.grid(axis="y", which="both", linestyle="--", alpha=0.35)

            latest = cur_values[-1]
            speedup = baseline / latest
            ax.text(
                0.98,
                0.95,
                f"Speedup vs baseline: {speedup:.2f}x",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=10,
                bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#bbbbbb"},
            )

            for b, v in zip(bars, cur_values):
                ax.text(
                    b.get_x() + b.get_width() / 2.0,
                    v * 1.05,
                    f"{int(v/1000)}k",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

            fig.tight_layout()
            frame_path = tmp_dir / f"speed_{i:02d}.png"
            fig.savefig(frame_path)
            plt.close(fig)
            images.append(Image.open(frame_path).convert("P", palette=Image.Palette.ADAPTIVE))

    out = ASSETS_DIR / "neural-speedup-progression.gif"
    images[0].save(
        out,
        save_all=True,
        append_images=images[1:],
        duration=550,
        loop=0,
        optimize=True,
    )
    return out


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out1 = make_character_generation_gif()
    out2 = make_speedup_progression_gif()
    print(f"Generated: {out1.relative_to(ROOT)}")
    print(f"Generated: {out2.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
