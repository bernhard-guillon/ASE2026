#!/usr/bin/env python3
"""
Build script for Phase-1 counter->char scaffold.

Creates a scaffold JSON from the existing character generator model with the
counter->a0 contract metadata.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], cwd: str | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    base_json = os.environ.get("COUNTER_CHAR_BASE_JSON")
    export_script = os.environ.get("COUNTER_CHAR_EXPORT_SCRIPT")
    output_path = os.environ.get("COUNTER_CHAR_JSON_OUTPUT")

    if not all([base_json, export_script, output_path]):
        print("ERROR: Missing required environment variables for counter-char scaffold build")
        return 1

    rc = _run(
        [
            sys.executable,
            export_script,
            "--base-json",
            base_json,
            "--output",
            output_path,
        ]
    )
    if rc != 0:
        print("ERROR: Failed to export counter-char scaffold JSON")
        return 1

    print("Successfully generated counter-char scaffold JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

