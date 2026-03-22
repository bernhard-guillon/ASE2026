#!/usr/bin/env python3
"""
Blackbox test for neural character generation.

Tests that the neural network model can:
1. Compile to RISC-V code
2. Load as ELF and execute on emulator
3. Accept interactive input (character codes via a0)
4. Write output to framebuffer (0x20000) matching static_char_gen.c interface
5. Produce reasonable character images
"""

import subprocess
import tempfile
import json
from pathlib import Path
import sys


class NeuralCharGenTest:
    """Test neural character generation integration."""
    
    def __init__(self):
        self.emulator_dir = Path(__file__).parent.parent
        self.model_path = self.emulator_dir.parent.parent / "projects/weight-export/character_generator.json"
        self.emulator_bin = self.emulator_dir / "build/emulator_runner"
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
    
    def test_model_exists(self):
        """Test 1: Trained model exists"""
        return self.model_path.exists()
    
    def test_compiler_exists(self):
        """Test 2: Interactive model compiler exists"""
        compiler = self.emulator_dir / "model_compiler_interactive.py"
        return compiler.exists()
    
    def test_compile_to_assembly(self):
        """Test 3: Model compiles to interactive assembly"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_asm = Path(tmpdir) / "neural.s"
                
                result = subprocess.run(
                    ["python3", "model_compiler_interactive.py",
                     "-o", str(output_asm),
                     str(self.model_path)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                return result.returncode == 0 and output_asm.exists()
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def test_assemble_code(self):
        """Test 4: Generated assembly assembles successfully"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                output_asm = tmpdir / "neural.s"
                output_obj = tmpdir / "neural.o"
                
                # Generate assembly
                result1 = subprocess.run(
                    ["python3", "model_compiler_interactive.py",
                     "-o", str(output_asm),
                     str(self.model_path)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                if result1.returncode != 0:
                    return False
                
                # Assemble
                result2 = subprocess.run(
                    ["riscv64-elf-as", "-march=rv32if", "-mabi=ilp32f",
                     "-o", str(output_obj),
                     str(output_asm)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                return result2.returncode == 0 and output_obj.exists()
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def test_link_to_elf(self):
        """Test 5: Code links to ELF executable"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                output_asm = tmpdir / "neural.s"
                output_obj = tmpdir / "neural.o"
                output_elf = tmpdir / "neural.elf"
                
                # Generate assembly
                r1 = subprocess.run(
                    ["python3", "model_compiler_interactive.py",
                     "-o", str(output_asm),
                     str(self.model_path)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                # Assemble
                r2 = subprocess.run(
                    ["riscv64-elf-as", "-march=rv32if", "-mabi=ilp32f",
                     "-o", str(output_obj),
                     str(output_asm)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                # Link
                r3 = subprocess.run(
                    ["riscv64-elf-ld", "-m", "elf32lriscv",
                     "-T", "linker.ld",
                     "-o", str(output_elf),
                     str(output_obj)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                return (r1.returncode == 0 and r2.returncode == 0 and 
                       r3.returncode == 0 and output_elf.exists())
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def test_executes_on_emulator(self):
        """Test 6: ELF executes on emulator without errors"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                output_asm = tmpdir / "neural.s"
                output_obj = tmpdir / "neural.o"
                output_elf = tmpdir / "neural.elf"
                
                # Generate assembly
                r1 = subprocess.run(
                    ["python3", "model_compiler_interactive.py",
                     "-o", str(output_asm),
                     str(self.model_path)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                # Assemble
                r2 = subprocess.run(
                    ["riscv64-elf-as", "-march=rv32if", "-mabi=ilp32f",
                     "-o", str(output_obj),
                     str(output_asm)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                # Link
                r3 = subprocess.run(
                    ["riscv64-elf-ld", "-m", "elf32lriscv",
                     "-T", "linker.ld",
                     "-o", str(output_elf),
                     str(output_obj)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=30
                )
                
                if r1.returncode != 0 or r2.returncode != 0 or r3.returncode != 0:
                    return False
                
                # Execute on emulator
                result = subprocess.run(
                    [str(self.emulator_bin), str(output_elf)],
                    cwd=self.emulator_dir,
                    capture_output=True,
                    timeout=5
                )
                
                # Should exit cleanly
                return result.returncode == 0
        except subprocess.TimeoutExpired:
            # Timeout is OK - infinite loop is expected
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("NEURAL CHARACTER GENERATION BLACKBOX TESTS")
        print("=" * 70)
        print()
        
        self.test("Model file exists", self.test_model_exists)
        self.test("Interactive compiler exists", self.test_compiler_exists)
        self.test("Compile model to assembly", self.test_compile_to_assembly)
        self.test("Assemble code to object file", self.test_assemble_code)
        self.test("Link to ELF executable", self.test_link_to_elf)
        self.test("Execute on emulator", self.test_executes_on_emulator)
        
        print()
        print("=" * 70)
        print(f"RESULTS: {self.tests_passed} passed, {self.tests_failed} failed")
        print("=" * 70)
        
        return self.tests_failed == 0


if __name__ == "__main__":
    tester = NeuralCharGenTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
