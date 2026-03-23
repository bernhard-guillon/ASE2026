#!/usr/bin/env python3
"""
Blackbox test for neural character generation - all 256 characters.
"""

import subprocess
import numpy as np
from pathlib import Path
import sys
import re

class NeuralCharTest:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.emulator_bin = self.emulator_dir / "build/emulator_runner"
        self.neural_elf = self.emulator_dir / "neural.elf"
        self.pytorch_ref = self.emulator_dir.parent / "character-generation/pytorch_all_256_chars.npy"
        
        self.pytorch_chars = np.load(self.pytorch_ref)
        print(f"Loaded PyTorch reference: {self.pytorch_chars.shape}")
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def extract_framebuffer_grid(self, output_text):
        """Extract 20x20 grid from framebuffer output."""
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', output_text)
        
        lines = clean_text.strip().split('\n')
        
        # Take first 20 non-empty lines and pad to 20 chars
        grid_lines = []
        for line in lines:
            # Skip truly empty lines (but keep lines with spaces)
            if len(line) == 0:
                continue
            
            # Pad or truncate to exactly 20 chars
            padded_line = (line + ' ' * 20)[:20]
            
            # Replace █ with # for consistency
            padded_line = padded_line.replace('█', '#')
            
            grid_lines.append(padded_line)
            
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
                 '--char', chr(ascii_code),
                 '--cycles', '5000000',
                 '--render-framebuffer'],
                cwd=self.emulator_dir,
                capture_output=True,
                text=True,
                timeout=10
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
