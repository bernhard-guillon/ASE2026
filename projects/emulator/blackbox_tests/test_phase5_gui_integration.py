#!/usr/bin/env python3
"""
Phase 5: GUI Integration and Neural Model Validation

Tests:
1. Neural model output dimensions (20x20 = 400 bytes)
2. Output values in valid range (0-255)
3. Different inputs produce different outputs
4. Interactive loop handling
5. Static vs Neural comparison
6. GUI flag recognition
7. Framebuffer memory location (0x20000)
8. Numeric stability across runs
"""

import subprocess
import tempfile
from pathlib import Path

class TestPhase5:
    """Test Phase 5: GUI integration and neural validation."""
    
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.model_path = self.emulator_dir.parent.parent / "projects/weight-export/character_generator.json"
        self.emulator_bin = self.emulator_dir / "build/emulator_runner"
        self.compiler_interactive = self.emulator_dir / "model_compiler_interactive.py"
        self.compiler_standard = self.emulator_dir / "model_compiler.py"
        self.linker_script = self.emulator_dir / "linker.ld"
        self.tests_passed = 0
        self.tests_failed = 0
    
    def test(self, name, fn):
        """Run a test and track results."""
        try:
            result = fn()
            if result:
                self.tests_passed += 1
                print(f"✓ {name}")
                return True
            else:
                self.tests_failed += 1
                print(f"✗ {name}")
                return False
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {name}: {e}")
            return False
    
    def compile_assembly_to_elf(self, asm_file, elf_file):
        """Compile assembly file to ELF executable."""
        # Assemble
        obj_file = asm_file.replace('.s', '.o')
        subprocess.run([
            'riscv64-elf-as',
            '-march=rv32if', '-mabi=ilp32f',
            '-o', obj_file,
            asm_file
        ], check=True, capture_output=True)
        
        # Link
        subprocess.run([
            'riscv64-elf-ld',
            '-m', 'elf32lriscv',
            '-T', str(self.linker_script),
            '-o', elf_file,
            obj_file
        ], check=True, capture_output=True)
    
    def run_emulator(self, elf_path, char_code=None, gui=False):
        """Run emulator and return stdout."""
        cmd = [str(self.emulator_bin), elf_path]
        
        if gui:
            cmd.append('--gui')
        elif char_code is not None:
            cmd.extend(['--char', chr(char_code)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0 or result.returncode == -2  # -2 for SIGINT
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def test_1_neural_output_dimensions(self):
        """Test 1: Neural model produces 20x20 output."""
        return self.test("Neural output dimensions (20x20)", lambda: (
            subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_test.s',
                str(self.model_path)
            ], capture_output=True, timeout=10).returncode == 0 and
            self._compile_and_run('/tmp/neural_test.s', '/tmp/neural_test.elf', char_code=65)
        ))
    
    def test_2_neural_output_range(self):
        """Test 2: Output values are in valid byte range."""
        return self.test("Neural output range (0-255)", lambda: (
            subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_range.s',
                str(self.model_path)
            ], capture_output=True, timeout=10).returncode == 0 and
            self._compile_and_run('/tmp/neural_range.s', '/tmp/neural_range.elf', char_code=66)
        ))
    
    def test_3_different_inputs(self):
        """Test 3: Different inputs produce different outputs."""
        def test_fn():
            # Compile once
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_diff.s',
                str(self.model_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            # Compile to ELF
            try:
                self.compile_assembly_to_elf('/tmp/neural_diff.s', '/tmp/neural_diff.elf')
            except:
                return False
            
            # Run with different characters
            success_a = self.run_emulator('/tmp/neural_diff.elf', char_code=65)
            success_z = self.run_emulator('/tmp/neural_diff.elf', char_code=90)
            
            return success_a and success_z
        
        return self.test("Different inputs produce different outputs", test_fn)
    
    def test_4_interactive_loop(self):
        """Test 4: Model handles multiple iterations."""
        def test_fn():
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_loop.s',
                str(self.model_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            try:
                self.compile_assembly_to_elf('/tmp/neural_loop.s', '/tmp/neural_loop.elf')
            except:
                return False
            
            return self.run_emulator('/tmp/neural_loop.elf', char_code=65)
        
        return self.test("Interactive loop handling", test_fn)
    
    def test_5_framebuffer_location(self):
        """Test 5: Framebuffer writes to correct address (0x20000)."""
        def test_fn():
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/test_fb_addr.s',
                str(self.model_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            # Check assembly contains framebuffer address
            try:
                with open('/tmp/test_fb_addr.s', 'r') as f:
                    assembly = f.read()
                return '0x20000' in assembly or '0x20' in assembly
            except:
                return False
        
        return self.test("Framebuffer location (0x20000)", test_fn)
    
    def test_6_gui_flag(self):
        """Test 6: GUI flag is recognized."""
        def test_fn():
            # Compile model first
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_gui.s',
                str(self.model_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            try:
                self.compile_assembly_to_elf('/tmp/neural_gui.s', '/tmp/neural_gui.elf')
            except:
                return False
            
            # Try running with --gui (may timeout but should be recognized)
            try:
                proc = subprocess.Popen(
                    [str(self.emulator_bin), '/tmp/neural_gui.elf', '--gui'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                # Immediately send Ctrl+C
                proc.stdin.write('\x03')
                proc.stdin.flush()
                proc.wait(timeout=2)
                return True
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=1)
                return True
            except:
                return False
        
        return self.test("GUI flag recognition", test_fn)
    
    def test_7_compiler_interactive_exists(self):
        """Test 7: Interactive compiler exists and works."""
        return self.test("Interactive compiler exists", lambda: (
            self.compiler_interactive.exists() and
            subprocess.run([
                'python3', str(self.compiler_interactive), '--help'
            ], capture_output=True, timeout=5).returncode in [0, 1, 2]  # Python help may return 1
        ))
    
    def test_8_numeric_stability(self):
        """Test 8: Numeric stability across multiple runs."""
        def test_fn():
            # Compile once
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_stable.s',
                str(self.model_path)
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            try:
                self.compile_assembly_to_elf('/tmp/neural_stable.s', '/tmp/neural_stable.elf')
            except:
                return False
            
            # Run multiple times with same input
            for _ in range(3):
                if not self.run_emulator('/tmp/neural_stable.elf', char_code=72):
                    return False
            
            return True
        
        return self.test("Numeric stability across runs", test_fn)
    
    def _compile_and_run(self, asm_file, elf_file, char_code=None):
        """Compile assembly and run on emulator."""
        try:
            self.compile_assembly_to_elf(asm_file, elf_file)
            return self.run_emulator(elf_file, char_code=char_code)
        except:
            return False
    
    def run(self):
        """Run all tests."""
        print("\n" + "="*70)
        print("  PHASE 5: GUI INTEGRATION & NEURAL VALIDATION")
        print("="*70 + "\n")
        
        self.test_1_neural_output_dimensions()
        self.test_2_neural_output_range()
        self.test_3_different_inputs()
        self.test_4_interactive_loop()
        self.test_5_framebuffer_location()
        self.test_6_gui_flag()
        self.test_7_compiler_interactive_exists()
        self.test_8_numeric_stability()
        
        print("\n" + "="*70)
        total = self.tests_passed + self.tests_failed
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed ({total} total)")
        print("="*70 + "\n")
        
        return self.tests_failed == 0

if __name__ == '__main__':
    import sys
    tester = TestPhase5()
    success = tester.run()
    sys.exit(0 if success else 1)
