#!/usr/bin/env python3
"""
Phase-1 scaffold exporter for counter->a0->char-gen integration.

This does not train/compose models yet. It wraps the existing character
generator JSON and stamps explicit contract metadata so follow-up phases can
build on a stable interface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export counter-char scaffold JSON")
    parser.add_argument("--base-json", required=True, help="Input character generator JSON")
    parser.add_argument("--output", required=True, help="Output scaffold JSON path")
    args = parser.parse_args()

    src = Path(args.base_json)
    dst = Path(args.output)
    if not src.exists():
        print(f"ERROR: base JSON not found: {src}")
        return 1

    payload = json.loads(src.read_text(encoding="utf-8"))
    metadata = payload.setdefault("metadata", {})
    metadata["counter_char_phase"] = "phase1_scaffold"
    metadata["counter_modulus"] = 255
    metadata["counter_range"] = [0, 254]
    metadata["bridge_register"] = "a0"
    metadata["bridge_mapping"] = "scalar_a0_to_onehot255"
    metadata["description"] = (
        "Phase 1 scaffold: existing char generator with locked counter->a0 contract "
        "(counter modulo 255 feeding a0, char-gen one-hot-255 input unchanged)."
    )

    dst.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote scaffold JSON to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

