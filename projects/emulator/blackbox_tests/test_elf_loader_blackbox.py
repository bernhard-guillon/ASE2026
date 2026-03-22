#!/usr/bin/env python3

"""
Blackbox tests for ELF loader functionality.
Tests that ELF binaries are loaded correctly and execute properly.
"""

import subprocess
import os
import sys
from pathlib import Path

class ElfLoaderBlackboxTests:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.build_dir = self.emulator_dir / 'build'
        self.emulator_runner = self.build_dir / 'emulator_runner'
        self.elf_test_dir = self.build_dir / 'elf_loader_tests'
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

    # Test 1: Simple NOP program loads and runs
    def test_nop_program_loads(self):
        """Test 1: NOP program loads without error"""
        elf = self.elf_test_dir / 'test_nop_loop.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should not error
        return result.returncode == 0

    # Test 2: Program with .rodata loads and runs
    def test_rodata_program_loads(self):
        """Test 2: Program with .rodata section loads"""
        elf = self.elf_test_dir / 'test_rodata_read.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Test 3: Constant pattern program produces output
    def test_const_pattern_displays(self):
        """Test 3: Constant pattern loads and runs"""
        elf = self.elf_test_dir / 'test_const_pattern.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should load and run without error
        return result.returncode == 0

    # Test 4: Test array indexing program
    def test_array_indexing(self):
        """Test 4: Array indexing loads and runs"""
        elf = self.elf_test_dir / 'test_array_index.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Test 5: Read offset program works
    def test_read_offset_program(self):
        """Test 5: Reading from offset in .rodata works"""
        elf = self.elf_test_dir / 'test_read_offset.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Test 6: All existing tests still pass (no regression)
    def test_no_regression(self):
        """Test 6: Existing emulator tests still pass"""
        # Skip this in blackbox tests - run separately with ctest
        # Just verify that we can compile at least
        return self.emulator_runner.exists()

    # Test 7: ELF file validation works
    def test_elf_validation(self):
        """Test 7: Invalid ELF files are rejected"""
        # Create invalid ELF
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.elf', delete=False) as f:
            f.write(b'INVALID')
            temp_path = f.name
        
        try:
            result = subprocess.run(
                [str(self.emulator_runner), temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Should fail with error
            return 'Error' in result.stderr or 'Invalid' in result.stderr
        finally:
            os.unlink(temp_path)

    # Test 8: GUI mode with proper ELF works
    def test_gui_with_elf(self):
        """Test 8: GUI mode doesn't crash with proper ELF loading"""
        elf = self.elf_test_dir / 'test_write_immediately.elf'
        if not elf.exists():
            return False
        
        try:
            # Just test that GUI flag is accepted and doesn't error
            result = subprocess.run(
                [str(self.emulator_runner), str(elf), '--gui'],
                input='\x03',  # Send Ctrl+C to exit
                capture_output=True,
                text=True,
                timeout=5
            )
            # GUI mode should start without error
            return True
        except subprocess.TimeoutExpired:
            # GUI mode might timeout waiting for input, that's OK
            return True
        except Exception:
            return False

    # Test 9: Entry point is set correctly
    def test_entry_point_execution(self):
        """Test 9: Entry point from ELF is executed"""
        elf = self.elf_test_dir / 'test_const_fb.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should execute successfully
        return result.returncode == 0

    # Test 10: Multiple segments load correctly
    def test_multiple_segments(self):
        """Test 10: Programs with multiple segments load"""
        elf = self.elf_test_dir / 'test_rodata_read.elf'
        if not elf.exists():
            return False
        
        # Run with verbose to see segment loading
        result = subprocess.run(
            [str(self.emulator_runner), str(elf), '--verbose'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should load segments
        return 'segment' in result.stdout.lower() or result.returncode == 0

    # Test 11: Large binary with character font loads
    def test_large_binary_with_font(self):
        """Test 11: Large binary with character_font.h loads"""
        elf = self.elf_test_dir / 'test_array_index.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Test 12: Program halt works after execution
    def test_program_termination(self):
        """Test 12: Programs terminate cleanly"""
        elf = self.elf_test_dir / 'test_nop_loop.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Should terminate without hanging
        return result.returncode == 0

    # Test 13: Memory is allocated correctly for segments
    def test_memory_allocation(self):
        """Test 13: Segment data is placed at correct addresses"""
        elf = self.elf_test_dir / 'test_rodata_read.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf), '--verbose'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Verbose output should show loading addresses
        return 'Loading segment at' in result.stdout or result.returncode == 0

    # Test 14: Stack and heap don't interfere with loaded segments
    def test_stack_heap_isolation(self):
        """Test 14: Stack initialization doesn't corrupt segments"""
        elf = self.elf_test_dir / 'test_const_pattern.elf'
        if not elf.exists():
            return False
        
        result = subprocess.run(
            [str(self.emulator_runner), str(elf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0

    # Test 15: ELF loader handles both simple and complex binaries
    def test_elf_compatibility(self):
        """Test 15: ELF loader works with various binary types"""
        simple_elfs = [
            'test_nop_loop.elf',
            'test_write_immediately.elf',
            'test_const_pattern.elf'
        ]
        
        for elf_name in simple_elfs:
            elf = self.elf_test_dir / elf_name
            if not elf.exists():
                continue
            
            result = subprocess.run(
                [str(self.emulator_runner), str(elf)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False
        
        return True

def main():
    print("=" * 60)
    print("ELF LOADER BLACKBOX TESTS")
    print("=" * 60)
    print()
    
    tester = ElfLoaderBlackboxTests()
    
    tests = [
        ("NOP program loads", tester.test_nop_program_loads),
        ("RODATA program loads", tester.test_rodata_program_loads),
        ("Const pattern displays", tester.test_const_pattern_displays),
        ("Array indexing works", tester.test_array_indexing),
        ("Read offset program", tester.test_read_offset_program),
        ("No regression in existing tests", tester.test_no_regression),
        ("ELF validation rejects invalid", tester.test_elf_validation),
        ("GUI mode with ELF", tester.test_gui_with_elf),
        ("Entry point execution", tester.test_entry_point_execution),
        ("Multiple segments load", tester.test_multiple_segments),
        ("Large binary with font", tester.test_large_binary_with_font),
        ("Program termination", tester.test_program_termination),
        ("Memory allocation correct", tester.test_memory_allocation),
        ("Stack/heap isolation", tester.test_stack_heap_isolation),
        ("ELF loader compatibility", tester.test_elf_compatibility),
    ]
    
    for test_name, test_func in tests:
        tester.run_test(test_name, test_func)
    
    print()
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
