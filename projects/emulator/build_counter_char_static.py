#!/usr/bin/env python3
"""Build script for static counter-chargen model."""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], cwd: str | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    offset_export = os.environ.get("COUNTER_CHAR_STATIC_OFFSET_EXPORT_SCRIPT")
    chargen_base = os.environ.get("COUNTER_CHAR_STATIC_CHARGEN_BASE_JSON")
    compose_script = os.environ.get("COUNTER_CHAR_STATIC_COMPOSE_SCRIPT")
    offset_out = os.environ.get("COUNTER_CHAR_STATIC_OFFSET_JSON_TEMP")
    chargen_out = os.environ.get("COUNTER_CHAR_STATIC_CHARGEN_JSON_TEMP")
    output_path = os.environ.get("COUNTER_CHAR_STATIC_COMBINED_JSON_OUTPUT")

    if not all([offset_export, chargen_base, compose_script, offset_out, chargen_out, output_path]):
        print("ERROR: Missing environment variables for static counter-chargen build")
        return 1

    # Export offset layer
    rc = _run([sys.executable, offset_export, "--output", offset_out])
    if rc != 0:
        print("ERROR: Failed to export offset layer model")
        return 1

    # Copy chargen base
    import shutil
    shutil.copy(chargen_base, chargen_out)

    # Compose
    rc = _run([
        sys.executable,
        compose_script,
        "--offset-json", offset_out,
        "--chargen-json", chargen_out,
        "--output", output_path,
    ])
    if rc != 0:
        print("ERROR: Failed to compose static models")
        return 1

    print("Successfully generated static counter-chargen model JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
