#!/usr/bin/env python3
"""
Blackbox test: Validate static character generator against font file

Tests that the static character generator produces output that matches
the expected patterns from character_font.h for all printable ASCII
characters (32-126).

Uses --cycles and --render-framebuffer flags to run and capture output.
"""

import subprocess
import os
import re
from pathlib import Path


def resolve_emulator_runner(emulator_dir: Path) -> Path:
    runner = os.environ.get("EMULATOR_RUNNER")
    if runner:
        return Path(runner)
    if os.environ.get("EMULATOR_BACKEND", "").lower() == "verilator":
        return emulator_dir / "hdl" / "sim" / "verilator_runner"
    return emulator_dir / "build" / "emulator_runner"

class StaticCharGenValidator:
    """Validate static character generator against font file."""
    
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.emulator_bin = resolve_emulator_runner(self.emulator_dir)
        self.static_elf = self.emulator_dir / "build/static_char_gen.elf"
        self.font_header = self.emulator_dir / "character_font.h"
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.char_results = {}
        
        # Extract font data
        self.font_data = self.extract_font_data()
    
    def extract_font_data(self):
        """Extract character patterns from character_font.h."""
        if not self.font_header.exists():
            raise FileNotFoundError(f"Font header not found: {self.font_header}")
        
        with open(self.font_header, 'r') as f:
            content = f.read()
        
        # Find all character definitions
        chars = re.findall(r'\{ /\* Character\s+(\d+) \*/(.*?)\},', content, re.DOTALL)
        
        font_data = {}
        for char_num, char_data in chars:
            char_code = int(char_num)
            # Extract pixel values
            numbers = re.findall(r'\d+', char_data)
            pixels = [int(n) for n in numbers[:400]]
            font_data[char_code] = pixels
        
        return font_data
    
    def run_emulator_capture(self, char_code, cycles=50000, timeout=5):
        """Run emulator and capture framebuffer output.
        
        Returns: 400 pixel values from framebuffer
        """
        try:
            result = subprocess.run(
                [str(self.emulator_bin), str(self.static_elf),
                 '--char', chr(char_code),
                 '--cycles', str(cycles),
                 '--render-framebuffer'],
                capture_output=True, text=True, timeout=timeout
            )
            
            # Remove ANSI escape codes
            output = result.stdout
            output = output.replace('\033[2J', '')  # Clear screen
            output = output.replace('\033[H', '')   # Move cursor home
            
            # Parse the terminal output to extract the 20x20 grid
            lines = output.split('\n')
            grid_lines = []
            
            for line in lines:
                # Skip empty lines
                if not line:
                    continue
                # Each grid line should be exactly 20 characters of # or space
                if len(line) == 20 and all(c in ' #' for c in line):
                    grid_lines.append(line)
                # Collect until we have 20 valid lines
                if len(grid_lines) == 20:
                    break
            
            if len(grid_lines) != 20:
                print(f"DEBUG: Got {len(grid_lines)} grid lines, expected 20")
                return None
            
            # Convert to pixel array (# = 255, space = 0)
            pixels = []
            for row in grid_lines:
                for char in row:
                    pixels.append(255 if char == '#' else 0)
            
            return pixels
        
        except Exception as e:
            print(f"DEBUG: Exception in run_emulator_capture: {e}")
            return None
    
    def compare_pixels(self, expected, actual):
        """Compare two pixel arrays.
        
        Returns: (matches_count, total, differences, match_percent)
        """
        if not actual or len(actual) != 400 or len(expected) != 400:
            return (0, 400, 400, 0.0)
        
        matches = 0
        differences = 0
        for i in range(400):
            exp_on = expected[i] > 127
            act_on = actual[i] > 127
            if exp_on == act_on:
                matches += 1
            else:
                differences += 1
        
        match_percent = (matches / 400) * 100.0
        return (matches, 400, differences, match_percent)
    
    def grid_to_visual(self, pixels):
        """Convert pixel array to visual grid."""
        grid = []
        for row in range(20):
            line = ""
            for col in range(20):
                idx = row * 20 + col
                pixel = pixels[idx]
                line += '#' if pixel > 127 else ' '
            grid.append(line)
        return grid
    
    def test_character(self, char_code):
        """Test a single character."""
        if char_code not in self.font_data:
            self.char_results[char_code] = {
                'passed': False,
                'reason': 'Character not in font',
                'matches': 0,
                'total': 400,
                'differences': 400,
                'match_percent': 0.0
            }
            self.tests_failed += 1
            return False
        
        expected_pixels = self.font_data[char_code]
        actual_pixels = self.run_emulator_capture(char_code)
        
        if actual_pixels is None:
            self.char_results[char_code] = {
                'passed': False,
                'reason': 'Failed to capture framebuffer',
                'expected': self.grid_to_visual(expected_pixels),
                'actual': None,
                'matches': 0,
                'total': 400,
                'differences': 400,
                'match_percent': 0.0
            }
            self.tests_failed += 1
            return False
        
        matches, total, diffs, percent = self.compare_pixels(expected_pixels, actual_pixels)
        
        # Consider match if at least 95% of pixels match
        passed = percent >= 95.0
        
        self.char_results[char_code] = {
            'passed': passed,
            'reason': 'OK' if passed else f'{diffs} pixel(s) differ',
            'expected': self.grid_to_visual(expected_pixels),
            'actual': self.grid_to_visual(actual_pixels),
            'matches': matches,
            'total': total,
            'differences': diffs,
            'match_percent': percent
        }
        
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        return passed
    
    def run_all_tests(self):
        """Test all printable ASCII characters (32-126)."""
        print("\n" + "="*70)
        print("STATIC CHARACTER GENERATOR VALIDATION TEST")
        print("Comparing framebuffer output with font patterns")
        print("="*70 + "\n")
        
        # Check prerequisites
        if not self.emulator_bin.exists():
            print("✗ Emulator not found at", self.emulator_bin)
            return False
        
        if not self.static_elf.exists():
            print("✗ Static char gen ELF not found at", self.static_elf)
            return False
        
        print(f"✓ Emulator found: {self.emulator_bin}")
        print(f"✓ Static generator ELF found: {self.static_elf}")
        print(f"✓ Font data loaded: {len(self.font_data)} characters")
        print()
        
        # Test all printable ASCII characters
        print("Testing characters (50000 cycles, rendering framebuffer)...\n")
        
        ascii_start = 32   # space
        ascii_end = 127    # DEL (exclusive)
        
        for char_code in range(ascii_start, ascii_end):
            char_display = chr(char_code) if 32 <= char_code < 127 else f"[{char_code}]"
            
            if self.test_character(char_code):
                result = self.char_results[char_code]
                print(f"  ✓ '{char_display}' (ASCII {char_code:3d}): {result['matches']}/{result['total']} pixels ({result['match_percent']:.0f}%)")
            else:
                result = self.char_results[char_code]
                matches = result.get('matches', 0)
                total = result.get('total', 400)
                print(f"  ✗ '{char_display}' (ASCII {char_code:3d}): {matches}/{total} pixels - {result['reason']}")
        
        print()
        print("="*70)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed out of {self.tests_passed + self.tests_failed}")
        print("="*70 + "\n")
        
        # Show detailed result for first failing test (if any)
        if self.tests_failed > 0:
            for char_code in range(32, 127):
                if char_code in self.char_results and not self.char_results[char_code]['passed']:
                    self.show_detailed_result(char_code)
                    break
        else:
            # Show sample passing character
            if 65 in self.char_results:
                self.show_detailed_result(65)
        
        return self.tests_failed == 0
    
    def show_detailed_result(self, char_code):
        """Show detailed comparison for a character."""
        if char_code not in self.char_results:
            return
        
        result = self.char_results[char_code]
        char_display = chr(char_code) if 32 <= char_code < 127 else f"[{char_code}]"
        
        print(f"Detailed Result for '{char_display}' (ASCII {char_code}):")
        print("-" * 70)
        
        expected_grid = result['expected']
        actual_grid = result['actual']
        
        if actual_grid:
            print("EXPECTED (from font)           ACTUAL (from emulator)")
            print("-" * 35 + "  " + "-" * 35)
            for i in range(20):
                exp_line = expected_grid[i] if i < len(expected_grid) else ""
                act_line = actual_grid[i] if i < len(actual_grid) else ""
                match = "✓" if exp_line == act_line else "✗"
                print(f"{exp_line}  {match}  {act_line}")
        else:
            print("EXPECTED (from font):")
            print("-" * 35)
            for row in expected_grid:
                print(row)
        
        print()
        print(f"Match: {result['matches']}/{result['total']} pixels ({result['match_percent']:.1f}%)")
        print(f"Differences: {result['differences']}")
        print(f"Status: {'PASS' if result['passed'] else 'FAIL'}")
        print()

if __name__ == '__main__':
    validator = StaticCharGenValidator()
    success = validator.run_all_tests()
    exit(0 if success else 1)
