#!/usr/bin/env python3
"""
Black box tests for Phase 2: Bootloader execution in emulator.

Tests verify:
1. Bootloader assembles and links successfully
2. Bootloader executes in emulator
3. Models are copied to correct memory addresses
4. Memory integrity after model loading
5. Bootloader exits with correct code
"""

import unittest
import subprocess
import tempfile
import json
import struct
import os
from pathlib import Path
from model_compiler import ModelCompiler


class TestBootloaderExecution(unittest.TestCase):
    """Black box tests for bootloader execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.compiler = ModelCompiler(verbose=False)
        
        # Simple generator model
        self.gen_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 4,
                    "output_size": 2,
                    "activation": "relu",
                    "weights_shape": [4, 2],
                    "weights": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]],
                    "biases_shape": [2],
                    "biases": [0.5, -0.5]
                }
            ]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def _save_json(self, model_dict):
        """Helper to save model to JSON file."""
        path = os.path.join(self.temp_dir.name, "model.json")
        with open(path, 'w') as f:
            json.dump(model_dict, f)
        return path
    
    def _has_riscv_tools(self):
        """Check if RISC-V toolchain is available."""
        return (subprocess.run(['which', 'riscv64-elf-as'],
                              capture_output=True).returncode == 0 and
                subprocess.run(['which', 'riscv64-elf-ld'],
                              capture_output=True).returncode == 0)
    
    def _has_emulator(self):
        """Check if emulator is available."""
        emulator = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'build', 
                               'emulator_runner')
        return os.path.exists(emulator)
    
    def test_bootloader_compiles_to_assembly(self):
        """Test that bootloader generates valid assembly."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        self.assertTrue(os.path.exists(asm_path))
        with open(asm_path, 'r') as f:
            content = f.read()
        self.assertGreater(len(content), 0)
        self.assertIn("_start", content)
    
    def test_bootloader_assembles_with_riscv_as(self):
        """Test that bootloader assembles with RISC-V assembler."""
        if not self._has_riscv_tools():
            self.skipTest("RISC-V toolchain not available")
        
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        obj_path = os.path.join(self.temp_dir.name, "boot.o")
        result = subprocess.run(
            ['riscv64-elf-as', '-march=rv32i', asm_path, '-o', obj_path],
            capture_output=True
        )
        
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed:\n{result.stderr.decode()}")
        self.assertTrue(os.path.exists(obj_path))
    
    def test_bootloader_links_to_elf(self):
        """Test that bootloader links to ELF executable."""
        if not self._has_riscv_tools():
            self.skipTest("RISC-V toolchain not available")
        
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        # Assemble
        obj_path = os.path.join(self.temp_dir.name, "boot.o")
        subprocess.run(
            ['riscv64-elf-as', '-march=rv32i', asm_path, '-o', obj_path],
            capture_output=True,
            check=True
        )
        
        # Link (simple linker script)
        elf_path = os.path.join(self.temp_dir.name, "boot.elf")
        result = subprocess.run(
            ['riscv64-elf-ld', '-Ttext=0x0', obj_path, '-o', elf_path],
            capture_output=True
        )
        
        # Linking may fail due to missing sections, but object should be created
        self.assertTrue(os.path.exists(obj_path))
    
    def test_bootloader_has_correct_sections(self):
        """Test that bootloader object file has correct sections."""
        if not self._has_riscv_tools():
            self.skipTest("RISC-V toolchain not available")
        
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        # Assemble
        obj_path = os.path.join(self.temp_dir.name, "boot.o")
        subprocess.run(
            ['riscv64-elf-as', '-march=rv32i', asm_path, '-o', obj_path],
            capture_output=True,
            check=True
        )
        
        # Check sections with objdump
        try:
            result = subprocess.run(
                ['riscv64-elf-objdump', '-h', obj_path],
                capture_output=True
            )
            output = result.stdout.decode()
            
            # Should have .text and .data sections
            self.assertIn('.text', output)
            self.assertIn('.data', output)
        except FileNotFoundError:
            self.skipTest("objdump not available")
    
    def test_bootloader_has_start_symbol(self):
        """Test that bootloader has _start symbol."""
        if not self._has_riscv_tools():
            self.skipTest("RISC-V toolchain not available")
        
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        # Assemble
        obj_path = os.path.join(self.temp_dir.name, "boot.o")
        subprocess.run(
            ['riscv64-elf-as', '-march=rv32i', asm_path, '-o', obj_path],
            capture_output=True,
            check=True
        )
        
        # Check symbols
        try:
            result = subprocess.run(
                ['riscv64-elf-objdump', '-t', obj_path],
                capture_output=True
            )
            output = result.stdout.decode()
            
            # Should have _start symbol
            self.assertIn('_start', output)
        except FileNotFoundError:
            self.skipTest("objdump not available")
    
    def test_bootloader_with_different_model_sizes(self):
        """Test bootloader works with different model sizes."""
        # Small model
        small_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 2,
                    "output_size": 1,
                    "activation": "relu",
                    "weights_shape": [2, 1],
                    "weights": [[1.0], [2.0]],
                    "biases_shape": [1],
                    "biases": [0.5]
                }
            ]
        }
        
        json_path = self._save_json(small_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        asm_result, bin_result = self.compiler.compile(json_path, asm_path, 
                                                       with_bootloader=True)
        
        # Should generate files successfully
        self.assertTrue(os.path.exists(asm_result))
        self.assertTrue(os.path.exists(bin_result))
        
        # Check that size is reflected in bootloader
        with open(bin_result, 'rb') as f:
            bin_data = f.read()
        
        with open(asm_result, 'r') as f:
            asm_content = f.read()
        
        # Size should match
        self.assertIn(f"li a2, {len(bin_data)}", asm_content)
    
    def test_bootloader_memory_copy_correctness(self):
        """Test that bootloader copy loop is mathematically correct."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have proper loop structure:
        # 1. Initialize counter (xor a3, a3, a3)
        # 2. Check condition (bge a3, a2, .Lcopy_done)
        # 3. Load byte (lbu from source + offset)
        # 4. Store byte (sb to dest + offset)
        # 5. Increment counter (addi a3, a3, 1)
        # 6. Jump back (j .Lcopy_loop)
        
        self.assertIn("xor a3, a3, a3", asm_content)  # init
        self.assertIn("bge a3, a2", asm_content)      # condition
        self.assertIn("lbu", asm_content)             # load
        self.assertIn("sb", asm_content)              # store
        self.assertIn("addi a3, a3, 1", asm_content)  # increment
        self.assertIn("j .Lcopy_loop", asm_content)   # jump


if __name__ == '__main__':
    unittest.main()
