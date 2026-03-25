#!/usr/bin/env python3
"""
Blackbox test for neural character generator model validation.

Compares neural model output with static character generator (reference).
Validates that neural model produces character-like patterns in framebuffer.
"""

import subprocess
import os
from pathlib import Path
import sys


def resolve_emulator_runner(emulator_dir: Path) -> Path:
    runner = os.environ.get("EMULATOR_RUNNER")
    if runner:
        return Path(runner)
    if os.environ.get("EMULATOR_BACKEND", "").lower() == "verilator":
        return emulator_dir / "hdl" / "sim" / "verilator_runner"
    return emulator_dir / "build" / "emulator_runner"

class NeuralCharGenValidator:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.emulator_bin = resolve_emulator_runner(self.emulator_dir)
        self.neural_elf = Path(__file__).parent.parent / "build" / "neural_chargen.elf"
        self.static_elf = Path(__file__).parent.parent / "build" / "static_char_gen.elf"
        
    def run_emulator_capture(self, elf_file, char_code, cycles=100000, timeout=10):
        """Run emulator and capture framebuffer output."""
        try:
            result = subprocess.run(
                [str(self.emulator_bin), str(elf_file),
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
                return None
            
            # Convert to pixel array (# = 255, space = 0)
            pixels = []
            for row in grid_lines:
                for char in row:
                    pixels.append(255 if char == '#' else 0)
            
            return pixels
        
        except Exception as e:
            return None
    
    def count_active_pixels(self, pixels):
        """Count pixels that are on (> 127)."""
        if not pixels:
            return 0
        return sum(1 for p in pixels if p > 127)
    
    def pixel_difference(self, pixels1, pixels2):
        """Calculate pixel difference between two grids."""
        if not pixels1 or not pixels2 or len(pixels1) != len(pixels2):
            return 400
        
        diff = 0
        for p1, p2 in zip(pixels1, pixels2):
            if (p1 > 127) != (p2 > 127):
                diff += 1
        return diff
    
    def test_character(self, char_code):
        """Test a single character.
        
        Returns:
            Tuple of (char, ascii, static_active, neural_active, difference, similarity)
        """
        char = chr(char_code)
        
        # Run static and neural models
        static_pixels = self.run_emulator_capture(self.static_elf, char_code)
        neural_pixels = self.run_emulator_capture(self.neural_elf, char_code, cycles=100000)
        
        if not static_pixels or not neural_pixels:
            return (char, char_code, 0, 0, 400, 0.0)
        
        # Count active pixels
        static_active = self.count_active_pixels(static_pixels)
        neural_active = self.count_active_pixels(neural_pixels)
        
        # Calculate difference (pixels where they disagree)
        diff = self.pixel_difference(static_pixels, neural_pixels)
        
        # Similarity as percentage of agreement
        similarity = 100.0 * (1.0 - diff / 400.0)
        
        return (char, char_code, static_active, neural_active, diff, similarity)
    
    def run_validation(self):
        """Run full validation test."""
        print("=" * 70)
        print("NEURAL CHARACTER GENERATOR VALIDATION TEST")
        print("Comparing neural model with static character generator reference")
        print("=" * 70)
        print()
        
        # Check files exist
        if not self.emulator_bin.exists():
            print(f"✗ Emulator not found: {self.emulator_bin}")
            return False
        if not self.neural_elf.exists():
            print(f"✗ Neural model ELF not found: {self.neural_elf}")
            print(f"  Run: python3 model_compiler_interactive.py -o neural_chargen.s ../weight-export/character_generator.json")
            return False
        if not self.static_elf.exists():
            print(f"✗ Static generator ELF not found: {self.static_elf}")
            return False
        
        print(f"✓ Emulator found: {self.emulator_bin}")
        print(f"✓ Neural model ELF found: {self.neural_elf}")
        print(f"✓ Static model ELF found: {self.static_elf}")
        print()
        
        # Test characters 32-126 (printable ASCII)
        print("Testing characters (100000 cycles per character)...")
        print()
        
        results = []
        for char_code in range(32, 127):
            result = self.test_character(char_code)
            results.append(result)
        
        # Print results table
        print("Char ASCII  Static  Neural  Diff   Similarity")
        print("-" * 50)
        for char, code, static_active, neural_active, diff, sim in results:
            char_display = char if char.isprintable() and char != ' ' else '·'
            print(f"  {char_display}   {code:3d}    {static_active:3d}    {neural_active:3d}    {diff:3d}    {sim:5.1f}%")
        
        print()
        print("=" * 70)
        
        # Summary statistics
        similarities = [sim for _, _, _, _, _, sim in results]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        high_agreement = sum(1 for sim in similarities if sim >= 95.0)
        good_agreement = sum(1 for sim in similarities if sim >= 80.0)
        
        print(f"Average similarity: {avg_similarity:.1f}%")
        print(f"High agreement (≥95%): {high_agreement}/95 characters")
        print(f"Good agreement (≥80%): {good_agreement}/95 characters")
        print()
        
        # Show distribution
        if high_agreement == 95:
            print("✓ Excellent: Neural and static models are highly aligned")
        elif good_agreement >= 85:
            print("✓ Good: Neural model shows reasonable correlation with static")
        elif avg_similarity >= 60:
            print("⚠ Moderate: Neural model shows some correlation")
        else:
            print("✗ Low: Neural model differs significantly from static")
        
        return True

if __name__ == "__main__":
    validator = NeuralCharGenValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
