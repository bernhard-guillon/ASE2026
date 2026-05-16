#!/usr/bin/env python3
"""
Build script for dual-model squash control chain.

Trains physics and counter models if checkpoints are missing and exports them.
Used by CMake dual_model_elf target.

Environment variables:
    DUAL_MODEL_PHYSICS_CHECKPOINT: Path to physics model checkpoint
    DUAL_MODEL_COUNTER_CHECKPOINT: Path to counter model checkpoint
    DUAL_MODEL_TRAIN_PHYSICS_SCRIPT: Path to train_physics.py
    DUAL_MODEL_TRAIN_COUNTER_SCRIPT: Path to train_counter.py
    DUAL_MODEL_EXPORT_SCRIPT: Path to export_dual_model.py
    DUAL_MODEL_PHYSICS_JSON_OUTPUT: Path to physics JSON output
    DUAL_MODEL_COUNTER_JSON_OUTPUT: Path to counter JSON output
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
    physics_checkpoint = os.environ.get("DUAL_MODEL_PHYSICS_CHECKPOINT")
    counter_checkpoint = os.environ.get("DUAL_MODEL_COUNTER_CHECKPOINT")
    train_physics_script = os.environ.get("DUAL_MODEL_TRAIN_PHYSICS_SCRIPT")
    train_counter_script = os.environ.get("DUAL_MODEL_TRAIN_COUNTER_SCRIPT")
    export_script = os.environ.get("DUAL_MODEL_EXPORT_SCRIPT")
    physics_json_output = os.environ.get("DUAL_MODEL_PHYSICS_JSON_OUTPUT")
    counter_json_output = os.environ.get("DUAL_MODEL_COUNTER_JSON_OUTPUT")

    if not all([
        physics_checkpoint,
        counter_checkpoint,
        train_physics_script,
        train_counter_script,
        export_script,
        physics_json_output,
        counter_json_output,
    ]):
        print("ERROR: Missing required environment variables for dual model build")
        print(f"  DUAL_MODEL_PHYSICS_CHECKPOINT={physics_checkpoint}")
        print(f"  DUAL_MODEL_COUNTER_CHECKPOINT={counter_checkpoint}")
        print(f"  DUAL_MODEL_TRAIN_PHYSICS_SCRIPT={train_physics_script}")
        print(f"  DUAL_MODEL_TRAIN_COUNTER_SCRIPT={train_counter_script}")
        print(f"  DUAL_MODEL_EXPORT_SCRIPT={export_script}")
        print(f"  DUAL_MODEL_PHYSICS_JSON_OUTPUT={physics_json_output}")
        print(f"  DUAL_MODEL_COUNTER_JSON_OUTPUT={counter_json_output}")
        return 1

    train_dir = os.path.dirname(train_physics_script)
    physics_checkpoint_path = Path(physics_checkpoint)
    counter_checkpoint_path = Path(counter_checkpoint)

    # Train physics model if needed
    if not physics_checkpoint_path.exists():
        print("Physics model checkpoint not found. Training physics model...")
        rc = _run(
            [sys.executable, "train_physics.py", "100", "64", "0.001"],
            cwd=train_dir,
        )
        if rc != 0:
            print("ERROR: Failed to train physics model")
            return 1
    else:
        print("Physics model checkpoint found.")

    # Train counter model if needed
    if not counter_checkpoint_path.exists():
        print("Counter model checkpoint not found. Training counter model...")
        rc = _run(
            [sys.executable, "train_counter.py", "100", "32", "0.01"],
            cwd=train_dir,
        )
        if rc != 0:
            print("ERROR: Failed to train counter model")
            return 1
    else:
        print("Counter model checkpoint found.")

    # Export both models
    print("Exporting dual models to JSON...")
    rc = _run(
        [
            sys.executable,
            export_script,
            "both",
            "--physics-checkpoint",
            physics_checkpoint,
            "--counter-checkpoint",
            counter_checkpoint,
            "--output-dir",
            os.path.dirname(physics_json_output),
        ],
        cwd=train_dir,
    )
    if rc != 0:
        print("ERROR: Failed to export models")
        return 1

    # Verify outputs exist
    physics_json_path = Path(physics_json_output)
    counter_json_path = Path(counter_json_output)
    
    if not physics_json_path.exists():
        print(f"ERROR: Physics JSON not found: {physics_json_path}")
        return 1
    if not counter_json_path.exists():
        print(f"ERROR: Counter JSON not found: {counter_json_path}")
        return 1

    print(f"Successfully generated physics model JSON: {physics_json_path}")
    print(f"Successfully generated counter model JSON: {counter_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
