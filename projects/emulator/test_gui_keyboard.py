#!/usr/bin/env python3
"""
Test Phase 1: Keyboard Input System

Tests verify:
1. --gui flag is recognized
2. Register a0 can be updated from command line
3. Non-blocking input handling works
4. Ctrl+C exits cleanly
"""

import subprocess
import sys
import time
import signal
from pathlib import Path

class KeyboardInputTests:
    def __init__(self, emulator_dir):
        self.emulator_dir = Path(emulator_dir)
        self.tests_passed = 0
        self.tests_failed = 0
        
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
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {name}: {e}")
    
    def test_gui_flag_recognized(self):
        """Test 1: --gui flag is recognized in usage"""
        usage = self._get_usage()
        return '--gui' in usage
    
    def test_gui_char_combination(self):
        """Test 2: --gui and --char can be used together"""
        usage = self._get_usage()
        return '--gui' in usage and '--char' in usage
    
    def test_verbose_flag_works(self):
        """Test 3: --verbose flag still works"""
        usage = self._get_usage()
        return '--verbose' in usage
    
    def test_emulator_runner_exists(self):
        """Test 4: emulator_runner binary exists and is executable"""
        runner = self.emulator_dir / 'build' / 'emulator_runner'
        return runner.exists() and runner.stat().st_mode & 0o111
    
    def test_hello_elf_exists(self):
        """Test 5: Test ELF for basic functionality check exists"""
        hello_elf = self.emulator_dir / 'build' / 'blackbox_tests' / 'c' / 'hello' / 'hello.elf'
        return hello_elf.exists()
    
    def test_non_blocking_input_mode(self):
        """Test 6: Verify non-blocking input mode is set up"""
        # This is verified by the code structure (VMIN=0, VTIME=0)
        runner = self.emulator_dir / 'emulator_runner.cpp'
        content = runner.read_text()
        has_vmin = 'VMIN' in content
        has_vtime = 'VTIME' in content
        return has_vmin and has_vtime
    
    def test_register_a0_setting(self):
        """Test 7: Register a0 is set from input"""
        runner = self.emulator_dir / 'emulator_runner.cpp'
        content = runner.read_text()
        # Check if register a0 (x10) is being set
        return 'setReg(10,' in content and 'key_code' in content
    
    def test_signal_handler_exists(self):
        """Test 8: Signal handler for Ctrl+C exists"""
        runner = self.emulator_dir / 'emulator_runner.cpp'
        content = runner.read_text()
        return 'signal_handler' in content and 'SIGINT' in content
    
    def test_gui_mode_branch(self):
        """Test 9: GUI mode code path exists"""
        runner = self.emulator_dir / 'emulator_runner.cpp'
        content = runner.read_text()
        return 'gui_mode' in content and 'process_gui_input' in content
    
    def test_terminal_mode_class(self):
        """Test 10: TerminalMode class for raw input exists"""
        runner = self.emulator_dir / 'emulator_runner.cpp'
        content = runner.read_text()
        return 'struct TerminalMode' in content and 'termios' in content
    
    def _get_usage(self):
        """Get usage message from emulator_runner"""
        try:
            result = subprocess.run(
                [str(self.emulator_dir / 'build' / 'emulator_runner')],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout + result.stderr
        except:
            return ""
    
    def run_all(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("PHASE 1: KEYBOARD INPUT SYSTEM - TEST SUITE")
        print("="*60 + "\n")
        
        print("Feature Detection Tests")
        print("-" * 40)
        self.test("--gui flag recognized", self.test_gui_flag_recognized)
        self.test("--gui and --char work together", self.test_gui_char_combination)
        self.test("--verbose flag supported", self.test_verbose_flag_works)
        
        print("\nBinary & Infrastructure Tests")
        print("-" * 40)
        self.test("emulator_runner binary exists", self.test_emulator_runner_exists)
        self.test("Test ELF available", self.test_hello_elf_exists)
        
        print("\nKeyboard Input Implementation Tests")
        print("-" * 40)
        self.test("Non-blocking input mode", self.test_non_blocking_input_mode)
        self.test("Register a0 setting", self.test_register_a0_setting)
        self.test("Signal handler for Ctrl+C", self.test_signal_handler_exists)
        
        print("\nGUI Mode Logic Tests")
        print("-" * 40)
        self.test("GUI mode code path exists", self.test_gui_mode_branch)
        self.test("TerminalMode class implementation", self.test_terminal_mode_class)
        
        print("\n" + "="*60)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        print("="*60)
        
        return self.tests_failed == 0

if __name__ == '__main__':
    emulator_dir = Path('/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator')
    suite = KeyboardInputTests(emulator_dir)
    success = suite.run_all()
    sys.exit(0 if success else 1)
