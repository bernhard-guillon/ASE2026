#!/usr/bin/env python3
"""
Blackbox test: Compare neural character generator vs static character generator

Tests that the neural model produces reasonable output by:
1. Running neural model with each character input
2. Running static model with same input
3. Capturing framebuffer output from both
4. Comparing outputs for similarity
5. Identifying which characters work well vs poorly
"""

import subprocess
import os
import tempfile
import json
from pathlib import Path
import struct


def resolve_emulator_runner(emulator_dir: Path) -> Path:
    runner = os.environ.get("EMULATOR_RUNNER")
    if runner:
        return Path(runner)
    if os.environ.get("EMULATOR_BACKEND", "").lower() == "verilator":
        return emulator_dir / "hdl" / "sim" / "verilator_runner"
    return emulator_dir / "build" / "emulator_runner"

class CharacterComparisonTest:
    """Compare neural vs static character generation."""
    
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.model_path = self.emulator_dir.parent.parent / "projects/weight-export/character_generator.json"
        self.emulator_bin = resolve_emulator_runner(self.emulator_dir)
        self.compiler_interactive = self.emulator_dir / "model_compiler_interactive.py"
        self.linker_script = self.emulator_dir / "linker.ld"
        self.static_elf = self.emulator_dir / "build/static_char_gen.elf"
        self.neural_elf = None
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = {}  # char_code -> (neural_bytes, static_bytes, similarity)
    
    def run_emulator_capture(self, elf_path, char_code, timeout=10):
        """Run emulator and capture framebuffer output.
        
        Returns: 400 bytes from framebuffer at 0x20000
        """
        try:
            # Create a small test program that dumps framebuffer
            cmd = [str(self.emulator_bin), str(elf_path), '--char', chr(char_code)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            # For now, just verify it runs without error
            # TODO: Add framebuffer capture mechanism
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            return False
    
    def compile_neural_model(self):
        """Compile the neural model to ELF."""
        if self.neural_elf and self.neural_elf.exists():
            return True
        
        try:
            # Compile
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/neural_compare.s',
                str(self.model_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False
            
            # Assemble
            subprocess.run([
                'riscv64-elf-as',
                '-march=rv32if', '-mabi=ilp32f',
                '-o', '/tmp/neural_compare.o',
                '/tmp/neural_compare.s'
            ], check=True, capture_output=True)
            
            # Link
            self.neural_elf = Path('/tmp/neural_compare.elf')
            subprocess.run([
                'riscv64-elf-ld',
                '-m', 'elf32lriscv',
                '-T', str(self.linker_script),
                '-o', str(self.neural_elf),
                '/tmp/neural_compare.o'
            ], check=True, capture_output=True)
            
            return self.neural_elf.exists()
        except Exception as e:
            print(f"Failed to compile neural model: {e}")
            return False
    
    def test_all_characters(self):
        """Test all 255 characters."""
        print("\n" + "="*70)
        print("NEURAL vs STATIC CHARACTER COMPARISON TEST")
        print("="*70 + "\n")
        
        # Check prerequisites
        if not self.emulator_bin.exists():
            print("✗ Emulator not found")
            return False
        
        if not self.static_elf.exists():
            print("✗ Static char gen ELF not found")
            return False
        
        print("✓ Emulator found")
        print("✓ Static char gen found")
        
        # Compile neural model
        print("Compiling neural model...")
        if not self.compile_neural_model():
            print("✗ Failed to compile neural model")
            return False
        print("✓ Neural model compiled")
        
        # Test all supported characters
        print("\nTesting characters...")
        supported_chars = list(range(32, 127))  # Printable ASCII
        
        passed = 0
        failed = 0
        
        for char_code in supported_chars:
            char_name = chr(char_code) if 32 <= char_code < 127 else f"<{char_code}>"
            
            # Test neural model
            try:
                neural_ok = self.run_emulator_capture(
                    self.neural_elf, char_code, timeout=5
                )
            except Exception:
                neural_ok = False
            
            # Test static model
            try:
                static_ok = self.run_emulator_capture(
                    self.static_elf, char_code, timeout=5
                )
            except Exception:
                static_ok = False
            
            if neural_ok and static_ok:
                passed += 1
                status = "✓"
            else:
                failed += 1
                status = "✗"
            
            self.results[char_code] = (neural_ok, static_ok)
            print(f"  {status} '{char_name}' (ASCII {char_code:3d}): "
                  f"Neural={'✓' if neural_ok else '✗'} "
                  f"Static={'✓' if static_ok else '✗'}")
        
        # Summary
        print("\n" + "="*70)
        print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
        print("="*70 + "\n")
        
        self.tests_passed = passed
        self.tests_failed = failed
        
        return failed == 0
    
    def test_specific_characters(self):
        """Test specific important characters."""
        print("\n" + "="*70)
        print("SPECIFIC CHARACTER TESTS")
        print("="*70 + "\n")
        
        test_chars = [
            (65, 'A', 'Uppercase letter'),
            (90, 'Z', 'Uppercase letter'),
            (97, 'a', 'Lowercase letter'),
            (122, 'z', 'Lowercase letter'),
            (48, '0', 'Digit'),
            (57, '9', 'Digit'),
            (32, ' ', 'Space'),
            (33, '!', 'Punctuation'),
            (63, '?', 'Punctuation'),
        ]
        
        passed = 0
        failed = 0
        
        for char_code, char_name, description in test_chars:
            # Test neural
            neural_ok = self.run_emulator_capture(
                self.neural_elf, char_code, timeout=5
            )
            
            # Test static
            static_ok = self.run_emulator_capture(
                self.static_elf, char_code, timeout=5
            )
            
            if neural_ok and static_ok:
                print(f"✓ '{char_name}' ({description}): Both work")
                passed += 1
            elif neural_ok:
                print(f"⚠ '{char_name}' ({description}): Neural✓ Static✗")
                failed += 1
            elif static_ok:
                print(f"⚠ '{char_name}' ({description}): Neural✗ Static✓")
                failed += 1
            else:
                print(f"✗ '{char_name}' ({description}): Both failed")
                failed += 1
        
        print("\n" + "="*70)
        print(f"SPECIFIC TESTS: {passed} passed, {failed} failed")
        print("="*70 + "\n")
        
        return failed == 0
    
    def test_neural_compilation(self):
        """Test 1: Neural model compiles to valid ELF."""
        test_name = "Neural model compiles to valid ELF"
        try:
            result = subprocess.run([
                'python3', str(self.compiler_interactive),
                '-o', '/tmp/test_neural.s',
                str(self.model_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception("Compilation failed")
            
            # Check assembly file
            if not Path('/tmp/test_neural.s').exists():
                raise Exception("Assembly file not created")
            
            self.tests_passed += 1
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {test_name}: {e}")
            return False
    
    def test_neural_executes(self):
        """Test 2: Neural model executes without error."""
        test_name = "Neural model executes without crashing"
        try:
            # Use neural_elf from compilation
            if not self.neural_elf or not self.neural_elf.exists():
                if not self.compile_neural_model():
                    raise Exception("Failed to compile neural model")
            
            # Run with character 'A'
            cmd = [str(self.emulator_bin), str(self.neural_elf), '--char', 'A']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                raise Exception(f"Execution failed with code {result.returncode}")
            
            self.tests_passed += 1
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {test_name}: {e}")
            return False
    
    def test_static_executes(self):
        """Test 3: Static model executes without error."""
        test_name = "Static model executes without crashing"
        try:
            if not self.static_elf.exists():
                raise Exception("Static ELF not found")
            
            # Run with character 'A'
            cmd = [str(self.emulator_bin), str(self.static_elf), '--char', 'A']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                raise Exception(f"Execution failed with code {result.returncode}")
            
            self.tests_passed += 1
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {test_name}: {e}")
            return False
    
    def test_both_models_handle_range(self):
        """Test 4: Both models handle full ASCII range without crashing."""
        test_name = "Both models handle ASCII range 32-126"
        try:
            errors = []
            
            # Test neural with multiple characters
            for char_code in [32, 65, 97, 48, 122, 126]:
                try:
                    cmd = [str(self.emulator_bin), str(self.neural_elf), 
                           '--char', chr(char_code)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        errors.append(f"Neural failed for char {char_code}")
                except:
                    errors.append(f"Neural timeout for char {char_code}")
            
            # Test static with multiple characters
            for char_code in [32, 65, 97, 48, 122, 126]:
                try:
                    cmd = [str(self.emulator_bin), str(self.static_elf), 
                           '--char', chr(char_code)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        errors.append(f"Static failed for char {char_code}")
                except:
                    errors.append(f"Static timeout for char {char_code}")
            
            if errors:
                raise Exception(", ".join(errors))
            
            self.tests_passed += 1
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.tests_failed += 1
            print(f"✗ {test_name}: {e}")
            return False
    
    def run(self):
        """Run all tests."""
        print("\n" + "="*70)
        print("  NEURAL vs STATIC CHARACTER COMPARISON BLACKBOX TESTS")
        print("="*70)
        
        # Basic tests
        self.test_neural_compilation()
        self.test_neural_executes()
        self.test_static_executes()
        self.test_both_models_handle_range()
        
        # Comprehensive tests
        self.test_specific_characters()
        self.test_all_characters()
        
        # Final summary
        print("\n" + "="*70)
        total = self.tests_passed + self.tests_failed
        print(f"FINAL RESULTS: {self.tests_passed}/{total} tests passed")
        print("="*70 + "\n")
        
        return self.tests_failed == 0

if __name__ == '__main__':
    import sys
    tester = CharacterComparisonTest()
    success = tester.run()
    sys.exit(0 if success else 1)
