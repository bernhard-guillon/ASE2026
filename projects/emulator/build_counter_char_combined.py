#!/usr/bin/env python3
"""
Build script for combined counter-chargen model.

Exports counter255 and chargen JSONs, then composes them.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], cwd: str | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    counter_export = os.environ.get("COUNTER_CHAR_COUNTER_EXPORT_SCRIPT")
    chargen_base = os.environ.get("COUNTER_CHAR_CHARGEN_BASE_JSON")
    compose_script = os.environ.get("COUNTER_CHAR_COMPOSE_SCRIPT")
    counter_out = os.environ.get("COUNTER_CHAR_COUNTER_JSON_TEMP")
    chargen_out = os.environ.get("COUNTER_CHAR_CHARGEN_JSON_TEMP")
    output_path = os.environ.get("COUNTER_CHAR_COMBINED_JSON_OUTPUT")

    if not all([counter_export, chargen_base, compose_script, counter_out, chargen_out, output_path]):
        print("ERROR: Missing environment variables for combined model build")
        return 1

    # Export counter255
    rc = _run([sys.executable, counter_export, "--output", counter_out])
    if rc != 0:
        print("ERROR: Failed to export counter255 model")
        return 1

    # Copy chargen base as temp (or apply scaffold if needed)
    import shutil
    shutil.copy(chargen_base, chargen_out)

    # Compose
    rc = _run([
        sys.executable,
        compose_script,
        "--counter-json", counter_out,
        "--chargen-json", chargen_out,
        "--output", output_path,
    ])
    if rc != 0:
        print("ERROR: Failed to compose models")
        return 1

    print("Successfully generated combined counter-chargen model JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
