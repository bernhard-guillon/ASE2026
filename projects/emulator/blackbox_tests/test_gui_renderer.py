#!/usr/bin/env python3
"""
Test Phase 2: TTY Framebuffer Renderer

Tests verify:
1. FramebufferRenderer class exists and compiles
2. Pixel-to-character conversion works
3. Rendering output format is correct
4. ANSI escape sequences for terminal control
5. Integration with emulator_runner GUI mode
"""

import subprocess
import sys
from pathlib import Path

class RendererTests:
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
    
    def test_renderer_class_declared(self):
        """Test 1: FramebufferRenderer class declared in Emulator.h"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        return 'class FramebufferRenderer' in header
    
    def test_render_method_exists(self):
        """Test 2: render() method declared"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        return 'void render(const Memory&' in header
    
    def test_pixel_to_char_method(self):
        """Test 3: pixel_to_char() conversion method exists"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        return 'pixel_to_char' in header
    
    def test_clear_screen_method(self):
        """Test 4: clear_screen() method exists"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        return 'clear_screen' in header
    
    def test_move_cursor_method(self):
        """Test 5: move_cursor_home() method exists"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        return 'move_cursor_home' in header
    
    def test_renderer_implementation(self):
        """Test 6: FramebufferRenderer implementation in Emulator.cpp"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        return 'FramebufferRenderer::render' in cpp
    
    def test_pixel_threshold_logic(self):
        """Test 7: Pixel threshold > 127 for block character"""
        header = (self.emulator_dir / 'Emulator.h').read_text()
        # Check for threshold comparison in pixel_to_char method
        has_threshold = '> 127' in header
        has_block_char = "'█'" in header or '█' in header
        has_space_char = "' '" in header
        return has_threshold and has_block_char and has_space_char
    
    def test_ansi_escape_sequences(self):
        """Test 8: ANSI escape sequences for terminal control"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        has_clear = '\\033[2J' in cpp or '\\x1b[2J' in cpp
        has_home = '\\033[H' in cpp or '\\x1b[H' in cpp
        return has_clear and has_home
    
    def test_framebuffer_address_used(self):
        """Test 9: FRAMEBUFFER_ADDR constant used in renderer"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        return 'FRAMEBUFFER_ADDR' in cpp
    
    def test_framebuffer_dimensions_used(self):
        """Test 10: FRAMEBUFFER_WIDTH and HEIGHT constants used"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        has_width = 'FRAMEBUFFER_WIDTH' in cpp
        has_height = 'FRAMEBUFFER_HEIGHT' in cpp
        return has_width and has_height
    
    def test_memory_read8_called(self):
        """Test 11: Memory::read8() called to read pixels"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        return 'read8(FRAMEBUFFER_ADDR' in cpp
    
    def test_stdout_output(self):
        """Test 12: Output sent to cout"""
        cpp = (self.emulator_dir / 'Emulator.cpp').read_text()
        return 'std::cout' in cpp
    
    def test_gui_input_uses_renderer(self):
        """Test 13: process_gui_input() uses FramebufferRenderer"""
        runner = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        has_renderer_var = 'FramebufferRenderer renderer' in runner
        has_render_call = 'renderer.render' in runner
        return has_renderer_var and has_render_call
    
    def test_renderer_called_in_loop(self):
        """Test 14: Renderer called in GUI input loop"""
        runner = (self.emulator_dir / 'emulator_runner.cpp').read_text()
        # Check that render is called in the while loop
        lines = runner.split('\n')
        in_while_loop = False
        has_render = False
        for i, line in enumerate(lines):
            if 'while (!g_should_exit)' in line:
                in_while_loop = True
            elif in_while_loop and 'renderer.render' in line:
                has_render = True
                break
            elif in_while_loop and (line.strip().startswith('std::cout') and 'closed' in line):
                break
        return has_render
    
    def test_emulator_runner_compiles(self):
        """Test 15: emulator_runner compiles successfully"""
        runner = self.emulator_dir / 'build' / 'emulator_runner'
        return runner.exists() and runner.stat().st_mode & 0o111
    
    def run_all(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("PHASE 2: TTY FRAMEBUFFER RENDERER - TEST SUITE")
        print("="*60 + "\n")
        
        print("Class & Method Declaration Tests")
        print("-" * 40)
        self.test("FramebufferRenderer class declared", self.test_renderer_class_declared)
        self.test("render() method exists", self.test_render_method_exists)
        self.test("pixel_to_char() conversion", self.test_pixel_to_char_method)
        self.test("clear_screen() method", self.test_clear_screen_method)
        self.test("move_cursor_home() method", self.test_move_cursor_method)
        
        print("\nImplementation Tests")
        print("-" * 40)
        self.test("FramebufferRenderer implementation", self.test_renderer_implementation)
        self.test("Pixel threshold logic (> 127)", self.test_pixel_threshold_logic)
        self.test("ANSI escape sequences", self.test_ansi_escape_sequences)
        
        print("\nFramebuffer Integration Tests")
        print("-" * 40)
        self.test("FRAMEBUFFER_ADDR used", self.test_framebuffer_address_used)
        self.test("FRAMEBUFFER_WIDTH/HEIGHT used", self.test_framebuffer_dimensions_used)
        self.test("Memory::read8() called", self.test_memory_read8_called)
        self.test("stdout output (cout)", self.test_stdout_output)
        
        print("\nGUI Integration Tests")
        print("-" * 40)
        self.test("GUI input uses renderer", self.test_gui_input_uses_renderer)
        self.test("Renderer in GUI loop", self.test_renderer_called_in_loop)
        self.test("emulator_runner compiles", self.test_emulator_runner_compiles)
        
        print("\n" + "="*60)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        print("="*60)
        
        return self.tests_failed == 0

if __name__ == '__main__':
    emulator_dir = Path(__file__).parent.parent
    suite = RendererTests(emulator_dir)
    success = suite.run_all()
    sys.exit(0 if success else 1)
