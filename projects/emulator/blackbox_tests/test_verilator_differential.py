#!/usr/bin/env python3
"""
Differential validation between emulator_runner and verilator_runner.

This test intentionally covers a broad set of binaries to close backend
coverage gaps:
1) Full parity sweep over all compiled asm/c blackbox ELFs.
2) Framebuffer parity on static/neural programs with multiple characters.
3) Performance/cycle reporting sanity on representative cases.
4) VCD trace generation sanity check.
"""

import subprocess
import tempfile
import time
import re
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
        self.neural_elf = self._resolve_neural_elf()
        self.neural_enhance_variants = self._resolve_neural_enhance_variants()
        self.neural_enhance_variant_set = set(self.neural_enhance_variants)

    def _resolve_build_dir(self) -> Path:
        candidate = self.emulator_dir / "build"
        if (candidate / "emulator_runner").exists() and (candidate / "verilator_runner").exists():
            return candidate
        raise FileNotFoundError(
            "Missing build directory artifacts. Configure/build with: cmake -S . -B build && cmake --build build"
        )

    def _resolve_neural_elf(self):
        for candidate in (
            self.build_dir / "neural-op-enhance.elf",
            self.build_dir / "neural-ai-opsx77.elf",
            self.build_dir / "neural_chargen.elf",
            self.build_dir / "neural.elf",
            self.emulator_dir / "neural.elf",
        ):
            if candidate.exists():
                return candidate
        return None

    def _resolve_neural_enhance_variants(self):
        variants = []
        for name in ("neural-op-enhance.elf", "neural-op-enhance4.elf", "neural-op-enhance8.elf"):
            candidate = self.build_dir / name
            if candidate.exists():
                variants.append(candidate)
        return variants

    def _seed_fs(self, work_dir: Path):
        (work_dir / "test_data.txt").write_text("seed-data\n", encoding="utf-8")

    def _run_cmd(
        self,
        runner: Path,
        elf: Path,
        args: list[str],
        work_dir: Path,
        *,
        timeout: int = 25,
    ):
        cmd = [str(runner), str(elf)] + args
        t0 = time.perf_counter()
        res = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return res, elapsed_ms

    def _assert_same(self, name: str, cpp_res: subprocess.CompletedProcess, vlt_res: subprocess.CompletedProcess):
        if cpp_res.returncode != vlt_res.returncode:
            raise AssertionError(
                f"{name}: rc mismatch cpp={cpp_res.returncode} vlt={vlt_res.returncode}"
            )
        if cpp_res.stdout != vlt_res.stdout:
            raise AssertionError(
                f"{name}: stdout mismatch\ncpp={cpp_res.stdout[:200]!r}\nvlt={vlt_res.stdout[:200]!r}"
            )
        if cpp_res.stderr != vlt_res.stderr:
            cpp_sys = re.search(r"(?:Unsupported|Unknown) syscall:\s*(\d+)", cpp_res.stderr)
            vlt_sys = re.search(r"(?:Unsupported|Unknown) syscall:\s*(\d+)", vlt_res.stderr)
            if cpp_sys and vlt_sys and cpp_sys.group(1) == vlt_sys.group(1):
                return
            raise AssertionError(
                f"{name}: stderr mismatch\ncpp={cpp_res.stderr[:200]!r}\nvlt={vlt_res.stderr[:200]!r}"
            )

    def _all_blackbox_elfs(self):
        asm_elfs = sorted((self.build_dir / "blackbox_tests" / "asm").glob("**/test.elf"))
        c_elfs = sorted((self.build_dir / "blackbox_tests" / "c").glob("**/*.elf"))
        return asm_elfs + c_elfs

    def run_full_blackbox_parity(self):
        all_elfs = self._all_blackbox_elfs()
        assert all_elfs, "No blackbox ELF artifacts discovered"

        print(f"blackbox parity: {len(all_elfs)} ELF(s)")
        for elf in all_elfs:
            rel = elf.relative_to(self.build_dir)
            case_name = str(rel)
            args = ["--cycles", "500000", "--dump-framebuffer"]

            with tempfile.TemporaryDirectory(prefix="cpp_case_") as cpp_td, tempfile.TemporaryDirectory(
                prefix="vlt_case_"
            ) as vlt_td:
                cpp_dir = Path(cpp_td)
                vlt_dir = Path(vlt_td)
                self._seed_fs(cpp_dir)
                self._seed_fs(vlt_dir)

                cpp_res, _ = self._run_cmd(self.cpp_runner, elf, args, cpp_dir)
                vlt_res, _ = self._run_cmd(self.verilator_runner, elf, args, vlt_dir)
                if "invalid_op_fail" in case_name:
                    assert cpp_res.returncode != 0 and vlt_res.returncode != 0, (
                        f"{case_name}: invalid-op fail-loud case unexpectedly succeeded "
                        f"(cpp={cpp_res.returncode}, vlt={vlt_res.returncode})"
                    )
                    continue
                if (
                    "nmatvec4x_invalid_flags" in case_name
                    or "nmatvec8x_invalid_flags" in case_name
                    or "nmatvec4x_invalid_reserved" in case_name
                    or "nmatvec8x_invalid_reserved" in case_name
                    or "nmatvec4x_overflow_ptr" in case_name
                    or "nmatvec8x_overflow_ptr" in case_name
                ):
                    assert cpp_res.returncode == 0 and vlt_res.returncode == 0, (
                        f"{case_name}: expected status-coded failure path, got "
                        f"cpp={cpp_res.returncode}, vlt={vlt_res.returncode}"
                    )
                self._assert_same(case_name, cpp_res, vlt_res)

        print("blackbox parity: PASS")

    def run_framebuffer_parity(self):
        assert self.static_elf.exists(), f"Missing static ELF: {self.static_elf}"
        fb_cases = [
            ("static-space", self.static_elf, 32, 500000),
            ("static-A", self.static_elf, 65, 500000),
            ("static-Z", self.static_elf, 90, 500000),
            ("static-z", self.static_elf, 122, 500000),
        ]
        if self.neural_elf is not None and self.neural_elf not in self.neural_enhance_variant_set:
            neural_cycles = 5000000 if self.neural_elf.name in ("neural-ai-opsx77.elf", "neural-op-enhance.elf") else 5000000
            fb_cases.extend(
                [
                    ("neural-A", self.neural_elf, 65, neural_cycles),
                    ("neural-z", self.neural_elf, 122, neural_cycles),
                ]
            )
        for enhance_elf in self.neural_enhance_variants:
            neural_cycles = 5000000
            tag = enhance_elf.stem
            fb_cases.extend(
                [
                    (f"{tag}-A", enhance_elf, 65, neural_cycles),
                    (f"{tag}-z", enhance_elf, 122, neural_cycles),
                ]
            )

        print(f"framebuffer parity: {len(fb_cases)} case(s)")
        for name, elf, char_code, cycles in fb_cases:
            args = [
                "--char-code",
                str(char_code),
                "--cycles",
                str(cycles),
                "--dump-framebuffer",
            ]
            with tempfile.TemporaryDirectory(prefix="cpp_fb_") as cpp_td, tempfile.TemporaryDirectory(
                prefix="vlt_fb_"
            ) as vlt_td:
                cpp_dir = Path(cpp_td)
                vlt_dir = Path(vlt_td)
                self._seed_fs(cpp_dir)
                self._seed_fs(vlt_dir)

                cpp_res, _ = self._run_cmd(self.cpp_runner, elf, args, cpp_dir, timeout=40)
                vlt_res, _ = self._run_cmd(self.verilator_runner, elf, args, vlt_dir, timeout=40)
                self._assert_same(name, cpp_res, vlt_res)
                assert _parse_framebuffer_hex(cpp_res.stdout) is not None, f"{name}: missing cpp framebuffer line"
                assert _parse_framebuffer_hex(vlt_res.stdout) is not None, f"{name}: missing vlt framebuffer line"
        print("framebuffer parity: PASS")

    def run_perf_sanity(self):
        perf_cases = [("static-A", self.static_elf, 65, 500000)]
        if self.neural_elf is not None and self.neural_elf not in self.neural_enhance_variant_set:
            neural_cycles = 5000000 if self.neural_elf.name in ("neural-ai-opsx77.elf", "neural-op-enhance.elf") else 2000000
            perf_cases.append(("neural-A", self.neural_elf, 65, neural_cycles))
        for enhance_elf in self.neural_enhance_variants:
            perf_cases.append((f"{enhance_elf.stem}-A", enhance_elf, 65, 5000000))

        print(f"performance sanity: {len(perf_cases)} case(s)")
        for name, elf, char_code, cycles in perf_cases:
            args = [
                "--char-code",
                str(char_code),
                "--cycles",
                str(cycles),
                "--dump-framebuffer",
                "--verbose",
            ]
            with tempfile.TemporaryDirectory(prefix="cpp_perf_") as cpp_td, tempfile.TemporaryDirectory(
                prefix="vlt_perf_"
            ) as vlt_td:
                cpp_dir = Path(cpp_td)
                vlt_dir = Path(vlt_td)
                self._seed_fs(cpp_dir)
                self._seed_fs(vlt_dir)

                cpp_res, cpp_ms = self._run_cmd(self.cpp_runner, elf, args, cpp_dir, timeout=40)
                vlt_res, vlt_ms = self._run_cmd(self.verilator_runner, elf, args, vlt_dir, timeout=40)

                assert cpp_res.returncode == vlt_res.returncode, (
                    f"{name}: return-code mismatch cpp={cpp_res.returncode} vlt={vlt_res.returncode}"
                )
                cpp_cycles = _parse_cycle_count(cpp_res.stdout)
                vlt_cycles = _parse_cycle_count(vlt_res.stdout)
                assert cpp_cycles is not None, f"{name}: missing cpp cycle report"
                assert vlt_cycles is not None, f"{name}: missing vlt cycle report"
                ratio = vlt_ms / cpp_ms if cpp_ms > 0 else 0.0
                print(
                    f"{name}: cycles cpp={cpp_cycles} vlt={vlt_cycles} "
                    f"time_ms cpp={cpp_ms:.1f} vlt={vlt_ms:.1f} ratio={ratio:.2f}x"
                )
        print("performance sanity: PASS")

    def run_trace_sanity(self):
        with tempfile.TemporaryDirectory(prefix="verilator_trace_") as td:
            trace_dir = Path(td)
            self._seed_fs(trace_dir)
            args = ["--char-code", "65", "--cycles", "100000", "--dump-framebuffer", "--trace"]
            res, _ = self._run_cmd(self.verilator_runner, self.static_elf, args, trace_dir, timeout=30)
            assert res.returncode == 0, f"trace run failed ({res.returncode})"
            assert _parse_framebuffer_hex(res.stdout) is not None, "trace run framebuffer dump missing"
            trace_file = trace_dir / "trace.vcd"
            assert trace_file.exists(), "trace.vcd was not generated"
            assert trace_file.stat().st_size > 0, "trace.vcd is empty"
            print(f"trace sanity: generated {trace_file.name} ({trace_file.stat().st_size} bytes)")

    def run(self):
        if not self.cpp_runner.exists():
            raise FileNotFoundError(f"Missing emulator runner: {self.cpp_runner}")
        if not self.verilator_runner.exists():
            raise FileNotFoundError(f"Missing verilator runner: {self.verilator_runner}")

        print("=== Verilator Differential Validation (Extended) ===")
        self.run_full_blackbox_parity()
        self.run_framebuffer_parity()
        self.run_perf_sanity()
        self.run_trace_sanity()
        print("=== Differential Validation: PASS ===")


def test_verilator_differential_validation():
    validator = DifferentialValidator()
    validator.run()


if __name__ == "__main__":
    test_verilator_differential_validation()
