#!/usr/bin/env python3
"""
Build script for standalone counter255 model JSON.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], cwd: str | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    export_script = os.environ.get("COUNTER255_EXPORT_SCRIPT")
    output_path = os.environ.get("COUNTER255_JSON_OUTPUT")

    if not all([export_script, output_path]):
        print("ERROR: Missing required environment variables for counter255 model build")
        return 1

    rc = _run([sys.executable, export_script, "--output", output_path])
    if rc != 0:
        print("ERROR: Failed to export counter255 model JSON")
        return 1

    print("Successfully generated counter255 model JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

