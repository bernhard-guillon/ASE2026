#!/usr/bin/env python3
"""
Blackbox test for neural character generation - all 256 characters.
"""

import subprocess
import os
import numpy as np
from pathlib import Path
import sys
import re
import shutil
import tempfile


def resolve_emulator_runner(emulator_dir: Path) -> Path:
    runner = os.environ.get("EMULATOR_RUNNER")
    if runner:
        return Path(runner)
    if os.environ.get("EMULATOR_BACKEND", "").lower() == "verilator":
        return emulator_dir / "hdl" / "sim" / "verilator_runner"
    return emulator_dir / "build" / "emulator_runner"

class NeuralCharTest:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.emulator_bin = resolve_emulator_runner(self.emulator_dir)
        self.neural_elf = self.emulator_dir / "neural.elf"
        self.compiler_script = self.emulator_dir / "model_compiler_interactive.py"
        self.model_json = self.emulator_dir.parent / "weight-export/character_generator.json"
        self.linker_script = self.emulator_dir / "linker.ld"
        self._build_dir = None
        self.pytorch_ref = self.emulator_dir.parent / "character-generation/pytorch_all_256_chars.npy"
        
        self.pytorch_chars = np.load(self.pytorch_ref)
        print(f"Loaded PyTorch reference: {self.pytorch_chars.shape}")
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
        self.cycles_per_char = int(os.environ.get("NEURAL_TEST_CYCLES", "100000"))
        self.emu_timeout_s = int(os.environ.get("NEURAL_TEST_TIMEOUT_S", "20"))

    def _find_tool(self, *names):
        """Return first available tool path for the given candidate names."""
        for name in names:
            tool = shutil.which(name)
            if tool:
                return tool
        return None

    def _rv32as_path(self) -> Path:
        override = os.environ.get("EMULATOR_NEW_ASSEMBLER")
        if override:
            return Path(override)
        return self.emulator_dir / "build" / "rv32as"

    def build_neural_elf(self):
        """Build neural ELF from model JSON for this test run."""
        if not self.compiler_script.exists():
            raise FileNotFoundError(f"Compiler script not found: {self.compiler_script}")
        if not self.model_json.exists():
            raise FileNotFoundError(f"Model JSON not found: {self.model_json}")
        if not self.linker_script.exists():
            raise FileNotFoundError(f"Linker script not found: {self.linker_script}")

        assembler = self._rv32as_path()
        linker = self._find_tool("riscv64-elf-ld", "riscv64-unknown-elf-ld")
        if not assembler.exists():
            raise RuntimeError(f"rv32as not found at {assembler}")
        if not linker:
            raise RuntimeError("RISC-V linker not found (riscv64-elf-ld/riscv64-unknown-elf-ld)")

        self._build_dir = tempfile.TemporaryDirectory(prefix="neural256_")
        build_dir = Path(self._build_dir.name)
        asm_path = build_dir / "neural.s"
        obj_path = build_dir / "neural.o"
        elf_path = build_dir / "neural.elf"

        compile_cmd = [
            sys.executable,
            str(self.compiler_script),
            "--use-neural-ops",
            "-o", str(asm_path),
            str(self.model_json)
        ]
        assemble_cmd = [
            str(assembler), str(asm_path), "-march", "rv32if", "-mabi", "ilp32f",
            "-o", str(obj_path)
        ]
        link_cmd = [
            linker, "-m", "elf32lriscv",
            "-T", str(self.linker_script),
            "-o", str(elf_path), str(obj_path)
        ]

        compile_result = subprocess.run(
            compile_cmd,
            cwd=self.emulator_dir,
            capture_output=True,
            text=True,
            timeout=180
        )
        if compile_result.returncode != 0:
            raise RuntimeError(f"Neural assembly generation failed:\n{compile_result.stderr}")

        assemble_result = subprocess.run(
            assemble_cmd,
            cwd=self.emulator_dir,
            capture_output=True,
            text=True,
            timeout=180
        )
        if assemble_result.returncode != 0:
            raise RuntimeError(f"Neural assembly step failed:\n{assemble_result.stderr}")

        link_result = subprocess.run(
            link_cmd,
            cwd=self.emulator_dir,
            capture_output=True,
            text=True,
            timeout=180
        )
        if link_result.returncode != 0:
            raise RuntimeError(f"Neural link step failed:\n{link_result.stderr}")

        self.neural_elf = elf_path
    
    def extract_framebuffer_grid(self, output_text):
        """Extract 20x20 grid from framebuffer output."""
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', output_text)

        # Keep leading/trailing blank rows from framebuffer output. Using strip()
        # here would remove valid all-space rows and break extraction.
        lines = clean_text.splitlines()

        grid_lines = []
        for line in lines:
            normalized = line.replace('█', '#')
            if len(normalized) == 0:
                continue
            if any(ch not in ' #' for ch in normalized):
                continue
            grid_lines.append((normalized + ' ' * 20)[:20])
            if len(grid_lines) == 20:
                break
        
        if len(grid_lines) != 20:
            return None
        
        # Convert to binary grid
        grid = np.zeros((20, 20), dtype=np.float32)
        for i, line in enumerate(grid_lines):
            for j, char in enumerate(line):
                if char == '#':
                    grid[i][j] = 1.0
        
        return grid
    
    def compare_grids(self, pytorch_grid, neural_grid):
        """Compare two 20x20 grids and return match percentage."""
        pytorch_binary = (pytorch_grid > 0.5).astype(np.float32)
        matches = np.sum(pytorch_binary == neural_grid)
        total = 20 * 20
        match_percent = (matches / total) * 100
        return match_percent
    
    def test_character(self, ascii_code):
        """Test a single character."""
        try:
            result = subprocess.run(
                [str(self.emulator_bin), str(self.neural_elf),
                 '--char-code', str(ascii_code),
                 '--cycles', str(self.cycles_per_char),
                 '--render-framebuffer'],
                cwd=self.emulator_dir,
                capture_output=True,
                text=True,
                timeout=self.emu_timeout_s
            )
            
            if result.returncode != 0:
                return None, None, f"Emulator error: {result.returncode}"
            
            neural_grid = self.extract_framebuffer_grid(result.stdout)
            if neural_grid is None:
                return None, None, "Failed to extract framebuffer grid"
            
            pytorch_grid = self.pytorch_chars[ascii_code]
            match_percent = self.compare_grids(pytorch_grid, neural_grid)
            
            return match_percent, neural_grid, None
            
        except subprocess.TimeoutExpired:
            return None, None, "Timeout"
        except Exception as e:
            return None, None, str(e)
    
    def run_all_tests(self):
        """Test all 256 characters."""
        print("=" * 70)
        print("NEURAL CHARACTER GENERATION - 256 CHARACTER TEST")
        print("=" * 70)
        print()

        self.build_neural_elf()
        print(f"Built neural ELF: {self.neural_elf}")
        print()
        
        for ascii_code in range(256):
            match_percent, neural_grid, error = self.test_character(ascii_code)
            
            if error:
                self.tests_failed += 1
                char_repr = chr(ascii_code) if 32 <= ascii_code <= 126 else f'\\x{ascii_code:02x}'
                result = {
                    'ascii': ascii_code,
                    'char': char_repr,
                    'match': 0.0,
                    'passed': False,
                    'error': error
                }
                print(f"✗ Char {ascii_code:3d} ({char_repr:4s}): {error}")
            else:
                passed = match_percent >= 80.0
                if passed:
                    self.tests_passed += 1
                else:
                    self.tests_failed += 1
                
                char_repr = chr(ascii_code) if 32 <= ascii_code <= 126 else f'\\x{ascii_code:02x}'
                result = {
                    'ascii': ascii_code,
                    'char': char_repr,
                    'match': match_percent,
                    'passed': passed,
                    'neural_grid': neural_grid,
                    'pytorch_grid': self.pytorch_chars[ascii_code]
                }
                
                status = "✓" if passed else "✗"
                print(f"{status} Char {ascii_code:3d} ({char_repr:4s}): {match_percent:5.1f}%")
            
            self.results.append(result)
            
            if (ascii_code + 1) % 32 == 0:
                print()
        
        print()
        print("=" * 70)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        if self.tests_passed + self.tests_failed > 0:
            print(f"Pass rate: {self.tests_passed / (self.tests_passed + self.tests_failed) * 100:.1f}%")
        print("=" * 70)
        
        return self.tests_failed == 0
    
    def show_passed_patterns(self):
        """Show patterns for passed tests."""
        print()
        print("=" * 70)
        print("PASSED TEST PATTERNS (first 10)")
        print("=" * 70)
        
        passed_tests = [r for r in self.results if r.get('passed', False)]
        
        for i, result in enumerate(passed_tests[:10]):
            print()
            print(f"Char {result['ascii']} ({result['char']}) - Match: {result['match']:.1f}%")
            print()
            print("PyTorch:             Neural:")
            
            pytorch_grid = result['pytorch_grid']
            neural_grid = result['neural_grid']
            
            for row_idx in range(20):
                pt_line = ''.join(['#' if pytorch_grid[row_idx][col] > 0.5 else ' ' for col in range(20)])
                nn_line = ''.join(['#' if neural_grid[row_idx][col] > 0.5 else ' ' for col in range(20)])
                print(f"{pt_line}   {nn_line}")
            print()

if __name__ == "__main__":
    tester = NeuralCharTest()
    success = tester.run_all_tests()
    tester.show_passed_patterns()
    sys.exit(0 if success else 1)
