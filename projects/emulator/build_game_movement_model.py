#!/usr/bin/env python3
"""
Build script for squash/game-movement model.

Trains squash model if checkpoint is missing and exports emulator JSON.
Used by CMake game_movement_elf target.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], cwd: str | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    checkpoint_path = os.environ.get("GAME_MOVEMENT_MODEL_CHECKPOINT")
    train_script = os.environ.get("GAME_MOVEMENT_TRAIN_SCRIPT")
    export_script = os.environ.get("GAME_MOVEMENT_EXPORT_SCRIPT")
    output_path = os.environ.get("GAME_MOVEMENT_JSON_OUTPUT")

    if not all([checkpoint_path, train_script, export_script, output_path]):
        print("ERROR: Missing required environment variables for game movement model build")
        return 1

    train_dir = os.path.dirname(train_script)

    if not os.path.exists(checkpoint_path):
        print("Game movement model checkpoint not found. Training squash model...")
        # Moderate defaults for build-path generation.
        rc = _run([sys.executable, "train_squash.py", "30", "128", "0.001", "400", "100"], cwd=train_dir)
        if rc != 0:
            print("ERROR: Failed to train squash model. Ensure torch/numpy are installed.")
            return 1

    print("Exporting game movement model to JSON...")
    rc = _run(
        [
            sys.executable,
            export_script,
            "--checkpoint",
            checkpoint_path,
            "--output",
            output_path,
        ],
        cwd=train_dir,
    )
    if rc != 0:
        print("ERROR: Failed to export game movement model JSON.")
        return 1

    print("Successfully generated game movement model JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
