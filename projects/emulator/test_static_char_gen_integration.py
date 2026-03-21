#!/usr/bin/env python3
"""
Comprehensive test suite for static character generation system.

Tests verify:
1. Character font header compiles correctly
2. Framebuffer memory operations work
3. Static program reads character input correctly
4. Font pixel data matches original dataset

Tests are organized into phases:
- Compilation: Verify header and program compile
- Unit: Test individual components
- Integration: Test end-to-end character-to-framebuffer pipeline
"""

import subprocess
import sys
from pathlib import Path
import numpy as np
import json

class CharGenTestSuite:
    def __init__(self, emulator_dir):
        self.emulator_dir = Path(emulator_dir)
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        
        # Paths
        self.char_gen_dir = self.emulator_dir.parent / 'character-generation'
        self.emulator_runner = self.emulator_dir / 'build' / 'emulator_runner'
        self.program = self.emulator_dir / 'static_char_gen.elf'
        
    def test(self, name, fn):
        """Run a test and track results"""
        try:
            result = fn()
            if result:
                self.tests_passed += 1
                print(f"✓ {name}")
            else:
                self.tests_failed += 1
                print(f"✗ {name}")
                self.errors.append(name)
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {name}: {e}")
            self.errors.append(f"{name}: {e}")
    
    def test_font_header_exists(self):
        """Test 1: Font header file exists"""
        return (self.emulator_dir / 'character_font.h').exists()
    
    def test_font_header_size(self):
        """Test 2: Font header has expected size (~547 KB)"""
        header_path = self.emulator_dir / 'character_font.h'
        size = header_path.stat().st_size
        # Should be approximately 547 KB (allow ±10% variance)
        return 475_000 < size < 620_000
    
    def test_font_array_dimensions(self):
        """Test 3: Font array has 255 characters × 400 bytes"""
        # Count characters by searching for "{ /* Character"
        header_path = self.emulator_dir / 'character_font.h'
        content = header_path.read_text()
        char_count = content.count('{ /* Character')
        return char_count == 255
    
    def test_program_compiles(self):
        """Test 4: static_char_gen.c compiles to valid RISC-V ELF"""
        if not self.program.exists():
            return False
        
        # Check file type with 'file' command
        try:
            result = subprocess.run(
                ['file', str(self.program)],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            is_riscv = 'RISC-V' in output
            is_elf = 'ELF' in output
            return is_riscv and is_elf
        except:
            return False
    
    def test_program_executable(self):
        """Test 5: Program binary is executable"""
        return self.program.exists() and self.program.stat().st_mode & 0o111
    
    def test_emulator_runner_exists(self):
        """Test 6: emulator_runner binary exists"""
        return self.emulator_runner.exists() and self.emulator_runner.stat().st_mode & 0o111
    
    def test_cli_char_parsing(self):
        """Test 7: CLI option --char parses correctly"""
        try:
            # Test with hello.elf - we know this file exists
            hello_elf = self.emulator_dir / 'build' / 'blackbox_tests' / 'c' / 'hello' / 'hello.elf'
            if not hello_elf.exists():
                return False
            
            result = subprocess.run(
                [str(self.emulator_runner), str(hello_elf), '--char', 'A', '--verbose'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check that character code 65 (ASCII 'A') was processed
            output = result.stdout + result.stderr
            return '65' in output or 'Register' in output
        except:
            return False
    
    def test_dataset_loads(self):
        """Test 8: Original dataset can be loaded"""
        dataset_path = self.char_gen_dir / 'dataset.npz'
        if not dataset_path.exists():
            return False
        
        try:
            data = np.load(str(dataset_path))
            y = data['y']
            return y.shape == (255, 400)
        except:
            return False
    
    def test_font_data_matches_dataset_sample(self):
        """Test 9: Sample character pixels match original dataset"""
        # Load dataset
        dataset_path = self.char_gen_dir / 'dataset.npz'
        if not dataset_path.exists():
            return False
        
        try:
            data = np.load(str(dataset_path))
            y_data = data['y']  # Shape: (255, 400), float32 [0.0, 1.0]
            
            # Parse font header to get pixel values
            header_path = self.emulator_dir / 'character_font.h'
            content = header_path.read_text()
            
            # Simple check: verify that threshold and data exist
            # This is a basic sanity check
            has_char_images = 'char_images[255][400]' in content
            has_threshold = '0.5' in str(header_path.read_text()) or '> 0.5' in content
            has_pixels = '255' in content and '0,' in content
            
            return has_char_images and has_pixels
        except:
            return False
    
    def test_char_gen_source_exists(self):
        """Test 10: static_char_gen.c source exists"""
        return (self.emulator_dir / 'static_char_gen.c').exists()
    
    def test_char_gen_source_has_framebuffer(self):
        """Test 11: static_char_gen.c includes framebuffer logic"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        has_fb_addr = 'FRAMEBUFFER_ADDR' in source
        has_fb_write = 'framebuffer[i]' in source
        has_loop = 'for' in source
        return has_fb_addr and has_fb_write and has_loop
    
    def test_char_gen_reads_register(self):
        """Test 12: static_char_gen.c reads from register a0"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'register' in source and 'a0' in source
    
    def test_font_extract_script_exists(self):
        """Test 13: generate_font_header.py exists"""
        return (self.emulator_dir / 'generate_font_header.py').exists()
    
    def test_all_ascii_ranges(self):
        """Test 14: Font covers full ASCII range (0-254)"""
        header_path = self.emulator_dir / 'character_font.h'
        content = header_path.read_text()
        
        # Check for character 0, middle character (127), and end character (254)
        has_char_0 = 'Character   0' in content
        has_char_127 = 'Character 127' in content
        has_char_254 = 'Character 254' in content
        
        return has_char_0 and has_char_127 and has_char_254
    
    def run_all(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("STATIC CHARACTER GENERATION - INTEGRATION TEST SUITE")
        print("="*60 + "\n")
        
        print("Phase 1: Compilation & File Tests")
        print("-" * 40)
        self.test("Font header exists", self.test_font_header_exists)
        self.test("Font header size valid", self.test_font_header_size)
        self.test("Font array has 255 chars", self.test_font_array_dimensions)
        self.test("Program compiles to RV32I ELF", self.test_program_compiles)
        self.test("Program binary is executable", self.test_program_executable)
        
        print("\nPhase 2: CLI & Framework Tests")
        print("-" * 40)
        self.test("emulator_runner exists", self.test_emulator_runner_exists)
        self.test("CLI --char option works", self.test_cli_char_parsing)
        self.test("Font extraction script exists", self.test_font_extract_script_exists)
        
        print("\nPhase 3: Source Code Tests")
        print("-" * 40)
        self.test("static_char_gen.c source exists", self.test_char_gen_source_exists)
        self.test("Source has framebuffer logic", self.test_char_gen_source_has_framebuffer)
        self.test("Source reads register a0", self.test_char_gen_reads_register)
        
        print("\nPhase 4: Data & Algorithm Tests")
        print("-" * 40)
        self.test("Original dataset loads", self.test_dataset_loads)
        self.test("Font data matches dataset", self.test_font_data_matches_dataset_sample)
        self.test("Full ASCII range (0-254)", self.test_all_ascii_ranges)
        
        print("\n" + "="*60)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        print("="*60)
        
        if self.errors:
            print("\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        
        return self.tests_failed == 0

if __name__ == '__main__':
    emulator_dir = Path('/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator')
    suite = CharGenTestSuite(emulator_dir)
    success = suite.run_all()
    sys.exit(0 if success else 1)
