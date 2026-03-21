#!/usr/bin/env python3
"""
Blackbox test runner for RV32I emulator.

Discovers test cases in blackbox_tests/, compiles them with GNU toolchain,
runs them in the emulator, and validates output against expected results.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import difflib

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class TestConfig:
    """Configuration loaded from config.txt"""
    exit_code: int = 0
    timeout_ms: int = 1000
    instruction_limit: int = 10000

@dataclass
class TestCase:
    """Represents a single test case"""
    name: str
    path: Path
    config: TestConfig

@dataclass
class TestResult:
    """Result of running a test"""
    name: str
    passed: bool
    expected_output: str
    actual_output: str
    expected_exit_code: int
    actual_exit_code: int
    error_message: Optional[str] = None

class BlackboxTestRunner:
    def __init__(self, emulator_dir: Path, emulator_runner: Path):
        self.emulator_dir = emulator_dir
        self.emulator_runner = emulator_runner
        self.tests_dir = emulator_dir / "blackbox_tests"
        self.build_dir = emulator_dir / "build_tests"
        
    def discover_tests(self) -> List[TestCase]:
        """Discover all test cases in blackbox_tests/"""
        tests = []
        
        if not self.tests_dir.exists():
            print(f"{Colors.RED}Error: blackbox_tests/ directory not found{Colors.RESET}")
            return tests
        
        # Search for test.s files
        for test_s in self.tests_dir.rglob("test.s"):
            test_dir = test_s.parent
            config_file = test_dir / "config.txt"
            expected_file = test_dir / "expected.txt"
            
            if not config_file.exists() or not expected_file.exists():
                print(f"{Colors.YELLOW}Warning: Skipping {test_dir} (missing config.txt or expected.txt){Colors.RESET}")
                continue
            
            # Parse config
            config = self._parse_config(config_file)
            
            # Get test name (relative path from blackbox_tests)
            test_name = str(test_dir.relative_to(self.tests_dir))
            
            tests.append(TestCase(
                name=test_name,
                path=test_dir,
                config=config
            ))
        
        return sorted(tests, key=lambda t: t.name)
    
    def _parse_config(self, config_file: Path) -> TestConfig:
        """Parse config.txt file"""
        config = TestConfig()
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'exit_code':
                            config.exit_code = int(value)
                        elif key == 'timeout_ms':
                            config.timeout_ms = int(value)
                        elif key == 'instruction_limit':
                            config.instruction_limit = int(value)
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Error parsing {config_file}: {e}{Colors.RESET}")
        
        return config
    
    def compile_test(self, test: TestCase) -> Tuple[bool, Optional[str]]:
        """Compile a single test case. Returns (success, error_message)"""
        test_s = test.path / "test.s"
        test_o = test.path / "test.o"
        test_elf = test.path / "test.elf"
        test_bin = test.path / "test.bin"
        
        # Assemble
        cmd = [
            "riscv64-elf-as",
            "-march=rv32i",
            "-mabi=ilp32",
            "-o", str(test_o),
            str(test_s)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Assembler error: {result.stderr}"
        
        # Link
        linker_script = self.emulator_dir / "linker.ld"
        cmd = [
            "riscv64-elf-ld",
            "-m", "elf32lriscv",
            "-T", str(linker_script),
            "-o", str(test_elf),
            str(test_o)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Linker error: {result.stderr}"
        
        # Convert to binary
        cmd = [
            "riscv64-elf-objcopy",
            "-O", "binary",
            str(test_elf),
            str(test_bin)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Objcopy error: {result.stderr}"
        
        return True, None
    
    def run_test(self, test: TestCase) -> TestResult:
        """Run a single test and return result"""
        test_bin = test.path / "test.bin"
        expected_file = test.path / "expected.txt"
        
        # Read expected output
        try:
            with open(expected_file, 'r') as f:
                expected_output = f.read()
        except Exception as e:
            return TestResult(
                name=test.name,
                passed=False,
                expected_output="",
                actual_output="",
                expected_exit_code=test.config.exit_code,
                actual_exit_code=-1,
                error_message=f"Failed to read expected.txt: {e}"
            )
        
        # Compile test
        success, error = self.compile_test(test)
        if not success:
            return TestResult(
                name=test.name,
                passed=False,
                expected_output=expected_output,
                actual_output="",
                expected_exit_code=test.config.exit_code,
                actual_exit_code=-1,
                error_message=error
            )
        
        # Run emulator
        timeout = test.config.timeout_ms / 1000.0
        try:
            result = subprocess.run(
                [str(self.emulator_runner), str(test_bin)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            actual_output = result.stdout
            actual_exit_code = result.returncode
        except subprocess.TimeoutExpired:
            return TestResult(
                name=test.name,
                passed=False,
                expected_output=expected_output,
                actual_output="",
                expected_exit_code=test.config.exit_code,
                actual_exit_code=-1,
                error_message=f"Timeout after {timeout}s"
            )
        except Exception as e:
            return TestResult(
                name=test.name,
                passed=False,
                expected_output=expected_output,
                actual_output="",
                expected_exit_code=test.config.exit_code,
                actual_exit_code=-1,
                error_message=f"Failed to run emulator: {e}"
            )
        
        # Validate output and exit code
        output_match = actual_output == expected_output
        exit_match = actual_exit_code == test.config.exit_code
        passed = output_match and exit_match
        
        return TestResult(
            name=test.name,
            passed=passed,
            expected_output=expected_output,
            actual_output=actual_output,
            expected_exit_code=test.config.exit_code,
            actual_exit_code=actual_exit_code
        )
    
    def run_all_tests(self, pattern: Optional[str] = None) -> List[TestResult]:
        """Run all discovered tests, optionally filtered by pattern"""
        tests = self.discover_tests()
        
        if pattern:
            tests = [t for t in tests if pattern in t.name]
        
        if not tests:
            print(f"{Colors.YELLOW}No tests found{Colors.RESET}")
            return []
        
        results = []
        for i, test in enumerate(tests, 1):
            print(f"[{i}/{len(tests)}] Running {test.name}...", end=" ")
            sys.stdout.flush()
            
            result = self.run_test(test)
            results.append(result)
            
            if result.passed:
                print(f"{Colors.GREEN}PASS{Colors.RESET}")
            else:
                print(f"{Colors.RED}FAIL{Colors.RESET}")
        
        return results
    
    def print_summary(self, results: List[TestResult], verbose: bool = False):
        """Print test results summary"""
        if not results:
            return
        
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"Test Results: {passed}/{len(results)} passed")
        print(f"{'='*60}{Colors.RESET}")
        
        if failed == 0:
            print(f"{Colors.GREEN}✓ All tests passed!{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ {failed} test(s) failed{Colors.RESET}")
            
            for result in results:
                if not result.passed:
                    print(f"\n{Colors.RED}FAILED: {result.name}{Colors.RESET}")
                    
                    if result.error_message:
                        print(f"  Error: {result.error_message}")
                    else:
                        if result.expected_exit_code != result.actual_exit_code:
                            print(f"  Exit code: expected {result.expected_exit_code}, got {result.actual_exit_code}")
                        
                        if result.expected_output != result.actual_output:
                            print(f"  Output mismatch:")
                            if verbose:
                                print(f"    Expected ({len(result.expected_output)} bytes):")
                                print(f"      {repr(result.expected_output)}")
                                print(f"    Got ({len(result.actual_output)} bytes):")
                                print(f"      {repr(result.actual_output)}")
                                
                                # Show unified diff
                                expected_lines = result.expected_output.splitlines(keepends=True)
                                actual_lines = result.actual_output.splitlines(keepends=True)
                                diff = difflib.unified_diff(
                                    expected_lines,
                                    actual_lines,
                                    fromfile="expected",
                                    tofile="actual",
                                    lineterm=''
                                )
                                for line in diff:
                                    print(f"    {line}", end='')
        
        print()

def main():
    parser = argparse.ArgumentParser(
        description="Blackbox test runner for RV32I emulator"
    )
    parser.add_argument(
        "-p", "--pattern",
        help="Run only tests matching this pattern"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output on failures"
    )
    parser.add_argument(
        "-d", "--directory",
        type=Path,
        default=Path.cwd(),
        help="Emulator project directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    emulator_dir = args.directory
    emulator_runner = emulator_dir / "build" / "emulator_runner"
    
    if not emulator_runner.exists():
        print(f"{Colors.RED}Error: emulator_runner not found at {emulator_runner}")
        print(f"Please build the emulator first: cd {emulator_dir}/build && cmake .. && cmake --build .{Colors.RESET}")
        sys.exit(1)
    
    runner = BlackboxTestRunner(emulator_dir, emulator_runner)
    results = runner.run_all_tests(args.pattern)
    runner.print_summary(results, verbose=args.verbose)
    
    # Exit with non-zero if any test failed
    if results and not all(r.passed for r in results):
        sys.exit(1)

if __name__ == "__main__":
    main()
