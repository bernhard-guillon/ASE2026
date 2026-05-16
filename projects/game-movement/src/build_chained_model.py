#!/usr/bin/env python3
"""
Build Script for Chained Dual-Model System (Option 4a).

Creates a chained model containing both physics and counter sub-networks
with only the explicit control bits (hit_wall, stop) wired between them.

The two sub-networks are NOT connected to each other - they only communicate
through the control signals as specified in the handoff document.

Used by CMake chained_model_elf target.

Environment Variables:
    CHAINED_MODEL_CHECKPOINT: Path to chained model checkpoint
    CHAINED_MODEL_EXPORT_SCRIPT: Path to export_chained.py
    CHAINED_MODEL_JSON_OUTPUT: Path to output JSON for emulator
    PHYSICS_MODEL_CHECKPOINT: Path to physics model checkpoint (optional)
    COUNTER_MODEL_CHECKPOINT: Path to counter model checkpoint (optional)
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
    chained_checkpoint = os.environ.get("CHAINED_MODEL_CHECKPOINT")
    export_script = os.environ.get("CHAINED_MODEL_EXPORT_SCRIPT")
    json_output = os.environ.get("CHAINED_MODEL_JSON_OUTPUT")
    physics_checkpoint = os.environ.get("PHYSICS_MODEL_CHECKPOINT")
    counter_checkpoint = os.environ.get("COUNTER_MODEL_CHECKPOINT")

    if not all([chained_checkpoint, export_script, json_output]):
        print("ERROR: Missing required environment variables for chained model build")
        print(f"  CHAINED_MODEL_CHECKPOINT={chained_checkpoint}")
        print(f"  CHAINED_MODEL_EXPORT_SCRIPT={export_script}")
        print(f"  CHAINED_MODEL_JSON_OUTPUT={json_output}")
        return 1

    train_dir = os.path.dirname(export_script)
    chained_path = Path(chained_checkpoint)

    # If chained checkpoint doesn't exist, create it by combining physics and counter models
    if not chained_path.exists():
        if not physics_checkpoint or not counter_checkpoint:
            print("ERROR: To create chained model, need both physics and counter checkpoints")
            print(f"  PHYSICS_MODEL_CHECKPOINT={physics_checkpoint}")
            print(f"  COUNTER_MODEL_CHECKPOINT={counter_checkpoint}")
            return 1
        
        print("Chained model checkpoint not found. Creating from sub-model checkpoints...")
        
        from chained_model import create_chained_model
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = create_chained_model(
            physics_checkpoint=physics_checkpoint,
            counter_checkpoint=counter_checkpoint,
            device=device,
        )
        
        # Save chained model
        checkpoint = {
            "model_state_dict": model.state_dict(),
            "input_size": 57,
            "output_size": 57,
        }
        torch.save(checkpoint, chained_checkpoint)
        print(f"Saved chained model to {chained_checkpoint}")
    else:
        print("Chained model checkpoint found.")

    # Export to JSON
    print("Exporting chained model to JSON...")
    rc = _run(
        [
            sys.executable,
            export_script,
            "--physics-checkpoint",
            physics_checkpoint or "",
            "--counter-checkpoint",
            counter_checkpoint or "",
            "--output",
            json_output,
        ],
        cwd=train_dir,
    )
    if rc != 0:
        print("ERROR: Failed to export chained model")
        return 1

    # Verify output
    output_path = Path(json_output)
    if not output_path.exists():
        print(f"ERROR: JSON output not found: {output_path}")
        return 1

    print(f"Successfully generated chained model JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
