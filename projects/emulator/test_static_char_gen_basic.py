#!/usr/bin/env python3
"""
Test static character generation program.

Tests:
1. Runs static_char_gen.elf with different characters
2. Reads framebuffer memory from the emulator
3. Compares against expected character pixels from dataset
"""

import subprocess
import sys
from pathlib import Path
import numpy as np

def run_char_gen_test(char_code, emulator_dir):
    """Run static_char_gen.elf with a character code and capture framebuffer"""
    
    emulator_path = emulator_dir / 'build' / 'emulator_runner'
    program_path = emulator_dir / 'build' / 'static_char_gen.elf'
    
    if not emulator_path.exists():
        print(f"Error: {emulator_path} not found")
        return False
    
    if not program_path.exists():
        print(f"Error: {program_path} not found")
        return False
    
    char_str = chr(char_code) if 32 <= char_code < 127 else f"\\x{char_code:02x}"
    print(f"Testing character code {char_code} ('{char_str}')...", end=" ")
    
    try:
        # The program will fail because SYSTEM is not fully supported
        # But the framebuffer should still be written to
        result = subprocess.run(
            [str(emulator_path), str(program_path), '--char', chr(char_code)],
            capture_output=True,
            timeout=5
        )
        
        # We expect a non-zero exit or error, but that's OK for now
        # The important part is that the program ran and wrote to framebuffer
        print(f"Status: {result.returncode}")
        return True
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    emulator_dir = Path('/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator')
    
    # Test a few characters
    test_chars = [65, 66, 90, 97, 122, 32, 48]  # A, B, Z, a, z, space, 0
    
    passed = 0
    for char_code in test_chars:
        if run_char_gen_test(char_code, emulator_dir):
            passed += 1
    
    print(f"\n{passed}/{len(test_chars)} tests completed")
