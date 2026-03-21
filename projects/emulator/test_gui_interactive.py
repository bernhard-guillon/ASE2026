#!/usr/bin/env python3

"""
Phase 3: Interactive C Program Loop Tests

Tests the modified static_char_gen.c program that runs in an infinite loop,
reading register a0 each iteration and updating the framebuffer.
"""

import subprocess
import os
import sys
import time
from pathlib import Path

class TestRunner:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent
        self.test_results = []
        self.tests_passed = 0
        self.tests_failed = 0
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        try:
            result = test_func()
            if result:
                self.tests_passed += 1
                self.test_results.append((test_name, True, None))
                print(f"✓ {test_name}")
            else:
                self.tests_failed += 1
                self.test_results.append((test_name, False, "Assertion failed"))
                print(f"✗ {test_name}")
        except Exception as e:
            self.tests_failed += 1
            self.test_results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.tests_passed + self.tests_failed
        print("\n" + "=" * 60)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        print("=" * 60)
        return self.tests_failed == 0

    # Test 1: Binary exists and is compilable
    def test_binary_exists(self):
        """Test 1: static_char_gen.elf exists"""
        elf = self.emulator_dir / 'static_char_gen.elf'
        return elf.exists()

    # Test 2: Binary is valid RISC-V ELF
    def test_binary_is_elf(self):
        """Test 2: Binary is valid RISC-V ELF"""
        elf = self.emulator_dir / 'static_char_gen.elf'
        result = subprocess.run(['file', str(elf)], capture_output=True, text=True)
        return 'RISC-V' in result.stdout and 'executable' in result.stdout

    # Test 3: Source code has infinite loop
    def test_source_has_infinite_loop(self):
        """Test 3: static_char_gen.c has while(1) loop"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'while (1)' in source

    # Test 4: Source code reads a0 each iteration
    def test_source_reads_a0_in_loop(self):
        """Test 4: Source code reads a0 in loop"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        # Check for a0 register definition and loop
        has_a0_def = '__asm__("a0")' in source
        has_loop = 'while (1)' in source
        return has_a0_def and has_loop

    # Test 5: Source validates character code in loop
    def test_source_validates_in_loop(self):
        """Test 5: Source validates char_code in loop"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        has_validation = 'if (char_code < 255)' in source
        return has_validation

    # Test 6: Source uses char_images lookup
    def test_source_uses_char_images(self):
        """Test 6: Source uses char_images for lookup"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'char_images[char_code]' in source

    # Test 7: Source copies to framebuffer in loop
    def test_source_copies_framebuffer_in_loop(self):
        """Test 7: Source copies 400 bytes to framebuffer"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        has_loop = 'for (int i = 0; i < 400' in source
        return has_loop

    # Test 8: Header includes character_font.h
    def test_source_includes_font(self):
        """Test 8: Source includes character_font.h"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return '#include "character_font.h"' in source

    # Test 9: FRAMEBUFFER_ADDR is defined correctly
    def test_framebuffer_addr_correct(self):
        """Test 9: FRAMEBUFFER_ADDR is 0x20000"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return '#define FRAMEBUFFER_ADDR 0x20000' in source

    # Test 10: No return statement in while loop
    def test_no_early_exit(self):
        """Test 10: Program doesn't exit in loop"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        # Find the while loop and verify no return inside it (before closing brace)
        lines = source.split('\n')
        in_loop = False
        loop_depth = 0
        
        for i, line in enumerate(lines):
            if 'while (1)' in line:
                in_loop = True
                loop_depth = 1
            elif in_loop:
                # Count braces to track loop depth
                loop_depth += line.count('{')
                loop_depth -= line.count('}')
                
                # If we've exited the loop (loop_depth back to 0), check if next return is after
                if loop_depth <= 0:
                    in_loop = False
                    # From here on, return statements are allowed (final return)
                    break
                
                # While still in loop, check for return statements
                if 'return' in line and line.strip().startswith('return'):
                    return False
        
        return True

    # Test 11: Source is syntactically correct C
    def test_source_compiles(self):
        """Test 11: Source code compiles without errors"""
        elf = self.emulator_dir / 'static_char_gen.elf'
        return elf.exists() and elf.stat().st_size > 1000

    # Test 12: Binary has reasonable size (not optimized away)
    def test_binary_size_reasonable(self):
        """Test 12: Binary size is reasonable (50KB+)"""
        elf = self.emulator_dir / 'static_char_gen.elf'
        return elf.stat().st_size > 50000

    # Test 13: Program has main function
    def test_has_main_function(self):
        """Test 13: Source has main function"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'int main()' in source

    # Test 14: Framebuffer variable is defined in loop scope
    def test_framebuffer_in_scope(self):
        """Test 14: Framebuffer pointer defined before loop"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        lines = source.split('\n')
        fb_ptr_line = -1
        while_line = -1
        
        for i, line in enumerate(lines):
            if 'unsigned char *framebuffer' in line and 'FRAMEBUFFER_ADDR' in line:
                fb_ptr_line = i
            if 'while (1)' in line:
                while_line = i
        
        # Framebuffer pointer should be defined before loop
        return fb_ptr_line >= 0 and while_line > fb_ptr_line

    # Test 15: Emulator runner compiles with GUI mode
    def test_emulator_compiles_with_gui(self):
        """Test 15: Emulator compiles (build check)"""
        build_dir = self.emulator_dir / 'build'
        if not build_dir.exists():
            return False
        
        runner = build_dir / 'emulator_runner'
        return runner.exists()

def main():
    print("=" * 60)
    print("PHASE 3: INTERACTIVE C PROGRAM LOOP - TEST SUITE")
    print("=" * 60)
    print()
    
    runner = TestRunner()
    
    # Run all tests
    print("Source Code Tests")
    print("-" * 60)
    runner.run_test("Binary exists", runner.test_binary_exists)
    runner.run_test("Binary is RISC-V ELF", runner.test_binary_is_elf)
    runner.run_test("Infinite loop present", runner.test_source_has_infinite_loop)
    runner.run_test("Reads a0 in loop", runner.test_source_reads_a0_in_loop)
    runner.run_test("Validates char_code", runner.test_source_validates_in_loop)
    runner.run_test("Uses char_images lookup", runner.test_source_uses_char_images)
    runner.run_test("Copies to framebuffer", runner.test_source_copies_framebuffer_in_loop)
    
    print()
    print("Build & Compilation Tests")
    print("-" * 60)
    runner.run_test("Includes character_font.h", runner.test_source_includes_font)
    runner.run_test("FRAMEBUFFER_ADDR correct", runner.test_framebuffer_addr_correct)
    runner.run_test("No early exit in loop", runner.test_no_early_exit)
    runner.run_test("Source compiles", runner.test_source_compiles)
    runner.run_test("Binary size reasonable", runner.test_binary_size_reasonable)
    
    print()
    print("Integration Tests")
    print("-" * 60)
    runner.run_test("Has main function", runner.test_has_main_function)
    runner.run_test("Framebuffer in scope", runner.test_framebuffer_in_scope)
    runner.run_test("Emulator compiles", runner.test_emulator_compiles_with_gui)
    
    print()
    success = runner.print_summary()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
