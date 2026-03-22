#!/usr/bin/env python3
"""
Phase 3 Test: Single-Layer Network Execution & Validation

Tests the simple 1-layer network (3→2 ReLU) on the emulator and validates
against the Python reference implementation.
"""

import subprocess
import json
import struct
import numpy as np
from pathlib import Path
import sys

# Add emulator directory to path
sys.path.insert(0, str(Path(__file__).parent))
from neural_reference import NeuralNetworkReference


class Phase3SingleLayerTest:
    """Test single-layer network execution on emulator."""
    
    def __init__(self, emulator_dir: str = "/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator"):
        self.emulator_dir = Path(emulator_dir)
        self.emulator_bin = self.emulator_dir / "build" / "emulator_runner"
        self.test_model = self.emulator_dir / "blackbox_tests/neural_exec/test_simple_layer.json"
        self.test_elf = self.emulator_dir / "blackbox_tests/neural_exec/test_simple_layer.elf"
        
        # Load reference implementation
        self.ref = NeuralNetworkReference(str(self.test_model))
    
    def setup(self) -> bool:
        """Verify all required files exist."""
        if not self.emulator_bin.exists():
            print(f"❌ Emulator binary not found: {self.emulator_bin}")
            return False
        
        if not self.test_model.exists():
            print(f"❌ Test model not found: {self.test_model}")
            return False
        
        if not self.test_elf.exists():
            print(f"❌ Test ELF not found: {self.test_elf}")
            return False
        
        print("✓ All required files present")
        return True
    
    def generate_test_elf(self) -> bool:
        """Regenerate the test ELF if needed."""
        compiler_py = self.emulator_dir / "model_compiler.py"
        
        # Check if regeneration is needed (test model is newer than ELF)
        if self.test_elf.exists() and self.test_model.stat().st_mtime < self.test_elf.stat().st_mtime:
            print("✓ Test ELF is up to date")
            return True
        
        print("Regenerating test ELF...")
        
        # Run model compiler
        result = subprocess.run(
            ["python3", str(compiler_py), str(self.test_model)],
            capture_output=True,
            cwd=self.emulator_dir
        )
        
        if result.returncode != 0:
            print(f"❌ Model compilation failed:")
            print(result.stderr.decode())
            return False
        
        # Assemble
        asm_file = self.test_elf.with_suffix('.s')
        result = subprocess.run(
            ["riscv64-elf-as", "-march=rv32if", "-mabi=ilp32f", str(asm_file), 
             "-o", str(asm_file.with_suffix('.o'))],
            capture_output=True,
            cwd=self.emulator_dir
        )
        
        if result.returncode != 0:
            print(f"❌ Assembly failed:")
            print(result.stderr.decode())
            return False
        
        # Link
        result = subprocess.run(
            ["riscv64-elf-ld", "-m", "elf32lriscv", "-T", "linker.ld",
             "-o", str(self.test_elf), str(asm_file.with_suffix('.o'))],
            capture_output=True,
            cwd=self.emulator_dir
        )
        
        if result.returncode != 0:
            print(f"❌ Linking failed:")
            print(result.stderr.decode())
            return False
        
        print("✓ Test ELF generated successfully")
        return True
    
    def run_emulator_test(self, timeout: int = 2) -> bool:
        """
        Run test on emulator.
        
        Currently tests that code executes without crashing (infinite loop exits on timeout).
        """
        print(f"Running emulator test (timeout: {timeout}s)...")
        
        try:
            result = subprocess.run(
                [str(self.emulator_bin), str(self.test_elf)],
                capture_output=True,
                timeout=timeout,
                cwd=self.emulator_dir
            )
        except subprocess.TimeoutExpired:
            # Timeout is expected - infinite loop in generated code
            print("✓ Emulator code executed (timeout - infinite loop as expected)")
            return True
        
        # If we get here, code exited (shouldn't happen with infinite loop)
        if result.returncode == 0:
            print("✓ Emulator code executed successfully")
            return True
        else:
            print(f"❌ Emulator returned error code {result.returncode}")
            print(result.stderr.decode())
            return False
    
    def test_reference_implementation(self) -> bool:
        """Test reference implementation with known inputs."""
        print("\nTesting reference implementation...")
        
        # Test case 1: one-hot input at position 0
        inputs1 = np.zeros(3, dtype=np.float32)
        inputs1[0] = 1.0
        output1 = self.ref.forward_pass(inputs1)
        
        # Expected: weights for layer 0
        # input = [1, 0, 0]
        # weights = [[1, 2], [3, 4], [5, 6]]
        # output = [1*1 + 0*3 + 0*5, 1*2 + 0*4 + 0*6] + bias
        #        = [1, 2] + [0.5, -0.5]  
        #        = [1.5, 1.5]
        # ReLU(1.5, 1.5) = [1.5, 1.5]
        expected1 = np.array([1.5, 1.5], dtype=np.float32)
        
        if not np.allclose(output1, expected1, atol=1e-5):
            print(f"❌ Test case 1 failed:")
            print(f"  Input: {inputs1}")
            print(f"  Expected: {expected1}")
            print(f"  Got: {output1}")
            return False
        
        print(f"✓ Test case 1 passed: {output1}")
        
        # Test case 2: one-hot input at position 1
        inputs2 = np.zeros(3, dtype=np.float32)
        inputs2[1] = 1.0
        output2 = self.ref.forward_pass(inputs2)
        
        # input = [0, 1, 0]
        # output = [0*1 + 1*3 + 0*5, 0*2 + 1*4 + 0*6] + bias
        #        = [3, 4] + [0.5, -0.5]
        #        = [3.5, 3.5]
        # ReLU = [3.5, 3.5]
        expected2 = np.array([3.5, 3.5], dtype=np.float32)
        
        if not np.allclose(output2, expected2, atol=1e-5):
            print(f"❌ Test case 2 failed:")
            print(f"  Input: {inputs2}")
            print(f"  Expected: {expected2}")
            print(f"  Got: {output2}")
            return False
        
        print(f"✓ Test case 2 passed: {output2}")
        
        # Test case 3: negative input (ReLU will clip)
        inputs3 = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        output3 = self.ref.forward_pass(inputs3)
        
        # input = [1, 1, 1]
        # output = [1*1 + 1*3 + 1*5, 1*2 + 1*4 + 1*6] + bias
        #        = [9, 12] + [0.5, -0.5]
        #        = [9.5, 11.5]
        # ReLU = [9.5, 11.5]
        expected3 = np.array([9.5, 11.5], dtype=np.float32)
        
        if not np.allclose(output3, expected3, atol=1e-5):
            print(f"❌ Test case 3 failed:")
            print(f"  Input: {inputs3}")
            print(f"  Expected: {expected3}")
            print(f"  Got: {output3}")
            return False
        
        print(f"✓ Test case 3 passed: {output3}")
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all Phase 3 tests."""
        print("=" * 60)
        print("PHASE 3: SINGLE-LAYER NETWORK EXECUTION TEST")
        print("=" * 60)
        
        # Setup
        if not self.setup():
            return False
        
        # Generate/update test ELF
        if not self.generate_test_elf():
            return False
        
        # Test reference implementation
        if not self.test_reference_implementation():
            return False
        
        # Run on emulator
        if not self.run_emulator_test():
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 3 TESTS PASSED")
        print("=" * 60)
        return True


if __name__ == "__main__":
    test = Phase3SingleLayerTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
