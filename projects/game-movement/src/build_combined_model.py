#!/usr/bin/env python3
"""
Build Script for Combined Dual-Model System.

Trains the combined model (Option 4a) if checkpoint is missing and exports it
to JSON format for the emulator's model compiler.

Used by CMake combined_model_elf target.

Environment Variables:
    COMBINED_MODEL_CHECKPOINT: Path to combined model checkpoint
    COMBINED_MODEL_TRAIN_SCRIPT: Path to train_combined.py
    COMBINED_MODEL_EXPORT_SCRIPT: Path to export_combined.py
    COMBINED_MODEL_JSON_OUTPUT: Path to output JSON for emulator
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: str | None = None) -> int:
    """Run a command and return its exit code."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result.returncode


def main() -> int:
    checkpoint_path = os.environ.get("COMBINED_MODEL_CHECKPOINT")
    train_script = os.environ.get("COMBINED_MODEL_TRAIN_SCRIPT")
    export_script = os.environ.get("COMBINED_MODEL_EXPORT_SCRIPT")
    json_output = os.environ.get("COMBINED_MODEL_JSON_OUTPUT")

    if not all([checkpoint_path, train_script, export_script, json_output]):
        print("ERROR: Missing required environment variables for combined model build")
        print(f"  COMBINED_MODEL_CHECKPOINT={checkpoint_path}")
        print(f"  COMBINED_MODEL_TRAIN_SCRIPT={train_script}")
        print(f"  COMBINED_MODEL_EXPORT_SCRIPT={export_script}")
        print(f"  COMBINED_MODEL_JSON_OUTPUT={json_output}")
        return 1

    train_dir = os.path.dirname(train_script)
    checkpoint = Path(checkpoint_path)

    # Train if checkpoint missing
    if not checkpoint.exists():
        print("Combined model checkpoint not found. Training combined model...")
        rc = _run(
            [sys.executable, "train_combined.py", "200", "32", "0.0001", "50", "200"],
            cwd=train_dir,
        )
        if rc != 0:
            print("ERROR: Failed to train combined model")
            return 1
    else:
        print("Combined model checkpoint found.")

    # Export to JSON
    print("Exporting combined model to JSON...")
    rc = _run(
        [
            sys.executable,
            export_script,
            "--checkpoint",
            checkpoint_path,
            "--output",
            json_output,
        ],
        cwd=train_dir,
    )
    if rc != 0:
        print("ERROR: Failed to export combined model")
        return 1

    # Verify output
    output_path = Path(json_output)
    if not output_path.exists():
        print(f"ERROR: JSON output not found: {output_path}")
        return 1

    print(f"Successfully generated combined model JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
