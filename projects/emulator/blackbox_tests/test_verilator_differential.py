#!/usr/bin/env python3
"""
Differential validation between emulator_runner and verilator_runner.

Runs the same ELF on both backends, compares framebuffer bytes, and reports
cycle/time deltas to track behavioral and performance differences.
"""

import subprocess
import time
import tempfile
from pathlib import Path


def _parse_framebuffer_hex(output: str):
    for line in output.splitlines():
        if line.startswith("FRAMEBUFFER_HEX:"):
            hex_data = line[len("FRAMEBUFFER_HEX:"):].strip()
            if len(hex_data) != 800:
                return None
            try:
                return bytes.fromhex(hex_data)
            except ValueError:
                return None
    return None


def _parse_cycle_count(output: str):
    for line in output.splitlines():
        if line.startswith("Cycles:"):
            try:
                return int(line.split(":")[-1].strip())
            except ValueError:
                return None
    for line in output.splitlines():
        if line.startswith("Execution complete. Cycles:"):
            try:
                return int(line.split(":")[-1].strip())
            except ValueError:
                return None
    return None


class DifferentialValidator:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.build_dir = self._resolve_build_dir()
        self.cpp_runner = self.build_dir / "emulator_runner"
        self.verilator_runner = self.build_dir / "verilator_runner"
        self.static_elf = self.build_dir / "static_char_gen.elf"
        self.asm_hello_elf = self.build_dir / "blackbox_tests" / "asm" / "basic" / "hello" / "test.elf"
        self.neural_elf = self._resolve_neural_elf()

    def _resolve_build_dir(self) -> Path:
        for name in ("build-ci", "build"):
            candidate = self.emulator_dir / name
            if (candidate / "emulator_runner").exists() and (candidate / "verilator_runner").exists():
                return candidate
        raise FileNotFoundError("Missing build directory with emulator_runner and verilator_runner")

    def _resolve_neural_elf(self):
        for candidate in (
            self.build_dir / "neural_chargen.elf",
            self.build_dir / "neural.elf",
            self.emulator_dir / "neural.elf",
        ):
            if candidate.exists():
                return candidate
        return None

    def _run_case(
        self,
        runner: Path,
        elf: Path,
        char_code: int,
        *,
        cycles: int = 5000000,
        trace: bool = False,
        cwd: Path | None = None,
    ):
        cmd = [
            str(runner),
            str(elf),
            "--char-code",
            str(char_code),
            "--cycles",
            str(cycles),
            "--dump-framebuffer",
            "--verbose",
        ]
        if trace:
            cmd.append("--trace")
        t0 = time.perf_counter()
        result = subprocess.run(
            cmd,
            cwd=cwd if cwd is not None else self.emulator_dir,
            capture_output=True,
            text=True,
            timeout=25,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        fb = _parse_framebuffer_hex(result.stdout)
        cycles = _parse_cycle_count(result.stdout)
        return result, fb, cycles, elapsed_ms

    def run(self):
        if not self.cpp_runner.exists():
            raise FileNotFoundError(f"Missing emulator runner: {self.cpp_runner}")
        if not self.verilator_runner.exists():
            raise FileNotFoundError(f"Missing verilator runner: {self.verilator_runner}")
        if not self.static_elf.exists():
            raise FileNotFoundError(f"Missing static ELF: {self.static_elf}")
        if not self.asm_hello_elf.exists():
            raise FileNotFoundError(f"Missing asm hello ELF: {self.asm_hello_elf}")

        cases = [
            ("static-A", self.static_elf, 65, 5000000),
            ("static-Z", self.static_elf, 90, 5000000),
        ]
        if self.neural_elf is not None:
            cases.extend([
                ("neural-A", self.neural_elf, 65, 1000000),
                ("neural-z", self.neural_elf, 122, 1000000),
            ])

        print("=== Verilator Differential Validation ===")
        for name, elf, char_code, cycles in cases:
            cpp_res, cpp_fb, cpp_cycles, cpp_ms = self._run_case(
                self.cpp_runner, elf, char_code, cycles=cycles
            )
            vlt_res, vlt_fb, vlt_cycles, vlt_ms = self._run_case(
                self.verilator_runner, elf, char_code, cycles=cycles
            )

            assert cpp_res.returncode == vlt_res.returncode, (
                f"{name}: return-code mismatch cpp={cpp_res.returncode} vlt={vlt_res.returncode}"
            )
            assert cpp_fb is not None, f"{name}: emulator_runner framebuffer dump missing"
            assert vlt_fb is not None, f"{name}: verilator_runner framebuffer dump missing"

            assert cpp_fb == vlt_fb, f"{name}: framebuffer mismatch"

            cycle_delta = None if (cpp_cycles is None or vlt_cycles is None) else (vlt_cycles - cpp_cycles)
            ratio = vlt_ms / cpp_ms if cpp_ms > 0 else 0.0
            print(
                f"{name}: fb=match"
                f", cycles cpp={cpp_cycles} vlt={vlt_cycles} delta={cycle_delta}"
                f", time_ms cpp={cpp_ms:.1f} vlt={vlt_ms:.1f} ratio={ratio:.2f}x"
            )

        with tempfile.TemporaryDirectory(prefix="verilator_trace_") as td:
            trace_dir = Path(td)
            trace_case_elf = self.static_elf
            trace_char = 65
            res, fb, _, _ = self._run_case(
                self.verilator_runner, trace_case_elf, trace_char, trace=True, cwd=trace_dir
            )
            assert res.returncode == 0, f"trace run failed ({res.returncode})"
            assert fb is not None, "trace run framebuffer dump missing"
            trace_file = trace_dir / "trace.vcd"
            assert trace_file.exists(), "trace.vcd was not generated"
            assert trace_file.stat().st_size > 0, "trace.vcd is empty"
            print(f"trace: generated {trace_file.name} ({trace_file.stat().st_size} bytes)")


def test_verilator_differential_validation():
    validator = DifferentialValidator()
    validator.run()


if __name__ == "__main__":
    test_verilator_differential_validation()
