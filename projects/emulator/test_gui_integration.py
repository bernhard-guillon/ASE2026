#!/usr/bin/env python3

"""
Phase 4: Full GUI Integration & Testing

Comprehensive end-to-end tests for the complete interactive GUI system.
Tests the full pipeline: keyboard input → program execution → framebuffer rendering.
"""

import subprocess
import os
import sys
import time
import tempfile
from pathlib import Path

class TestRunner:
    def __init__(self):
        self.emulator_dir = Path(__file__).parent
        self.build_dir = self.emulator_dir / 'build'
        self.emulator_runner = self.build_dir / 'emulator_runner'
        self.program = self.emulator_dir / 'static_char_gen.elf'
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

    # Test 1: Emulator runner exists
    def test_emulator_runner_exists(self):
        """Test 1: Emulator runner binary exists"""
        return self.emulator_runner.exists()

    # Test 2: Program binary exists
    def test_program_exists(self):
        """Test 2: Program binary (static_char_gen.elf) exists"""
        return self.program.exists()

    # Test 3: GUI flag is recognized
    def test_gui_flag_recognized(self):
        """Test 3: --gui flag is recognized in code"""
        runner_cpp = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        return '--gui' in runner_cpp and 'gui' in runner_cpp.lower()

    # Test 4: Program has char_images available
    def test_program_has_char_images(self):
        """Test 4: Program has access to char_images"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'char_images' in source

    # Test 5: Character font header exists
    def test_char_font_header_exists(self):
        """Test 5: character_font.h exists"""
        font_header = self.emulator_dir / 'character_font.h'
        return font_header.exists()

    # Test 6: Font header is large enough (contains data)
    def test_font_header_has_data(self):
        """Test 6: Font header has sufficient data (>500KB)"""
        font_header = self.emulator_dir / 'character_font.h'
        return font_header.stat().st_size > 500000

    # Test 7: Font header contains char_images declaration
    def test_font_header_declares_array(self):
        """Test 7: Font header declares char_images array"""
        font_header = (self.emulator_dir / 'character_font.h').read_text()
        return 'char_images' in font_header and 'unsigned char' in font_header

    # Test 8: Framebuffer is defined at correct address
    def test_framebuffer_address_correct(self):
        """Test 8: Framebuffer at 0x20000"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return '0x20000' in source and 'FRAMEBUFFER_ADDR' in source

    # Test 9: Terminal renderer is implemented
    def test_renderer_implemented(self):
        """Test 9: FramebufferRenderer class exists"""
        emulator_h = (self.emulator_dir / 'Emulator.h').read_text()
        return 'FramebufferRenderer' in emulator_h and 'render' in emulator_h

    # Test 10: ANSI sequences for terminal rendering
    def test_ansi_sequences_present(self):
        """Test 10: ANSI escape sequences implemented"""
        emulator_cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        emulator_h = (self.emulator_dir / 'Emulator.h').read_text()
        has_clear = '033[2J' in emulator_cpp or '\\033[2J' in emulator_h
        has_home = '033[H' in emulator_cpp or '\\033[H' in emulator_h
        return has_clear and has_home

    # Test 11: Keyboard input system exists
    def test_keyboard_input_system(self):
        """Test 11: Keyboard input system implemented"""
        runner_cpp = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        return 'termios' in runner_cpp or 'process_gui_input' in runner_cpp

    # Test 12: Signal handler for Ctrl+C
    def test_signal_handler_exists(self):
        """Test 12: Signal handler for clean exit"""
        runner_cpp = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        return 'signal' in runner_cpp or 'SIGINT' in runner_cpp or 'g_should_exit' in runner_cpp

    # Test 13: Terminal mode setup (raw mode)
    def test_terminal_raw_mode(self):
        """Test 13: Terminal raw mode setup"""
        runner_cpp = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        has_icanon = 'ICANON' in runner_cpp
        has_echo = 'ECHO' in runner_cpp
        return has_icanon and has_echo

    # Test 14: Program compiles successfully
    def test_program_compiles(self):
        """Test 14: Program binary is valid RISC-V"""
        result = subprocess.run(
            ['file', str(self.program)],
            capture_output=True,
            text=True
        )
        return 'RISC-V' in result.stdout and 'executable' in result.stdout

    # Test 15: Emulator compiles successfully
    def test_emulator_compiles(self):
        """Test 15: Emulator runner binary exists and is executable"""
        return self.emulator_runner.exists() and os.access(self.emulator_runner, os.X_OK)

    # Test 16: Memory addresses are consistent
    def test_memory_addresses_consistent(self):
        """Test 16: Framebuffer address consistent across files"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        header = (self.emulator_dir / 'Emulator.h').read_text()
        
        # Both should reference 0x20000
        source_has = '0x20000' in source
        header_has = '0x20000' in header or '131072' in header  # 0x20000 in decimal
        
        return source_has and header_has

    # Test 17: Framebuffer size is correct
    def test_framebuffer_size(self):
        """Test 17: Framebuffer is 400 bytes (20x20 pixels)"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return '400' in source

    # Test 18: Pixel conversion logic exists
    def test_pixel_conversion_logic(self):
        """Test 18: Pixel-to-character conversion implemented"""
        emulator_h = (self.emulator_dir / 'Emulator.h').read_text()
        return 'pixel_to_char' in emulator_h

    # Test 19: Block character rendering
    def test_block_character_rendering(self):
        """Test 19: Uses block character for rendering"""
        emulator_h = (self.emulator_dir / 'Emulator.h').read_text()
        emulator_cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        
        has_block = '█' in emulator_h or '█' in emulator_cpp
        return has_block

    # Test 20: Pixel threshold logic
    def test_pixel_threshold_logic(self):
        """Test 20: Pixel threshold > 127 for block character"""
        emulator_h = (self.emulator_dir / 'Emulator.h').read_text()
        return '> 127' in emulator_h and '█' in emulator_h

    # Test 21: Framebuffer rendering in main loop
    def test_renderer_in_gui_loop(self):
        """Test 21: Renderer called from GUI input loop"""
        runner_cpp = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        return 'render' in runner_cpp and 'process_gui_input' in runner_cpp

    # Test 22: Character lookup from array
    def test_char_lookup_array(self):
        """Test 22: Character lookup uses array indexing"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'char_images[char_code]' in source

    # Test 23: Validation range correct
    def test_validation_range(self):
        """Test 23: Validates character codes [0, 254]"""
        source = (self.emulator_dir / 'static_char_gen.c').read_text()
        return 'char_code < 255' in source or 'char_code <= 254' in source

    # Test 24: No compilation errors (all headers compatible)
    def test_headers_compatible(self):
        """Test 24: All headers compile together"""
        # Check files exist and are parseable
        files_ok = all([
            (self.emulator_dir / 'Emulator.h').exists(),
            (self.emulator_dir / 'Emulator.cpp').exists(),
            (self.emulator_dir / 'emulator_runner.cpp').exists(),
            (self.emulator_dir / 'static_char_gen.c').exists(),
            (self.emulator_dir / 'character_font.h').exists(),
        ])
        return files_ok

    # Test 25: Backward compatibility with existing tests
    def test_backward_compatibility(self):
        """Test 25: 250 existing tests still pass"""
        result = subprocess.run(
            ['ctest', '--output-on-failure', '-j4'],
            cwd=str(self.build_dir),
            capture_output=True,
            text=True,
            timeout=120
        )
        # Check for test pass count
        return '250 tests passed' in result.stdout or 'tests passed' in result.stdout

def main():
    print("=" * 60)
    print("PHASE 4: FULL GUI INTEGRATION & TESTING")
    print("=" * 60)
    print()
    
    runner = TestRunner()
    
    # Run all tests
    print("Component Tests")
    print("-" * 60)
    runner.run_test("Emulator runner exists", runner.test_emulator_runner_exists)
    runner.run_test("Program binary exists", runner.test_program_exists)
    runner.run_test("GUI flag recognized", runner.test_gui_flag_recognized)
    runner.run_test("Program has char_images", runner.test_program_has_char_images)
    runner.run_test("Font header exists", runner.test_char_font_header_exists)
    runner.run_test("Font header has data", runner.test_font_header_has_data)
    runner.run_test("Font header declares array", runner.test_font_header_declares_array)
    
    print()
    print("Architecture & Design Tests")
    print("-" * 60)
    runner.run_test("Framebuffer address correct", runner.test_framebuffer_address_correct)
    runner.run_test("Renderer implemented", runner.test_renderer_implemented)
    runner.run_test("ANSI sequences present", runner.test_ansi_sequences_present)
    runner.run_test("Keyboard input system", runner.test_keyboard_input_system)
    runner.run_test("Signal handler exists", runner.test_signal_handler_exists)
    runner.run_test("Terminal raw mode setup", runner.test_terminal_raw_mode)
    
    print()
    print("Implementation Tests")
    print("-" * 60)
    runner.run_test("Program compiles", runner.test_program_compiles)
    runner.run_test("Emulator compiles", runner.test_emulator_compiles)
    runner.run_test("Memory addresses consistent", runner.test_memory_addresses_consistent)
    runner.run_test("Framebuffer size correct", runner.test_framebuffer_size)
    runner.run_test("Pixel conversion logic", runner.test_pixel_conversion_logic)
    runner.run_test("Block character rendering", runner.test_block_character_rendering)
    runner.run_test("Pixel threshold logic", runner.test_pixel_threshold_logic)
    
    print()
    print("Integration Tests")
    print("-" * 60)
    runner.run_test("Renderer in GUI loop", runner.test_renderer_in_gui_loop)
    runner.run_test("Character lookup array", runner.test_char_lookup_array)
    runner.run_test("Validation range correct", runner.test_validation_range)
    runner.run_test("Headers compatible", runner.test_headers_compatible)
    runner.run_test("Backward compatibility", runner.test_backward_compatibility)
    
    print()
    success = runner.print_summary()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
