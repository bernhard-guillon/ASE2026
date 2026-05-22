#!/usr/bin/env python3
"""
Black box tests for model_compiler.py (Phase 1).

Tests verify:
1. Generated assembly can be assembled with RISC-V assembler
2. Object files have correct sections
3. Data section contains embedded binary
4. Assembly output is valid RV32IF
"""

import unittest
import subprocess
import tempfile
import json
import os
import struct
from pathlib import Path
from model_compiler import ModelCompiler


class TestModelCompilerBlackBox(unittest.TestCase):
    """Black box tests for ModelCompiler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.compiler = ModelCompiler(verbose=False)
        
        # Simple test model
        self.simple_model = {
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
                    "weights": [
                        [1.0, 2.0],
                        [3.0, 4.0],
                        [5.0, 6.0],
                        [7.0, 8.0]
                    ],
                    "biases_shape": [2],
                    "biases": [0.5, -0.5]
                }
            ]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def _save_json(self, model_dict, name="model.json"):
        """Helper to save model to JSON file."""
        path = os.path.join(self.temp_dir.name, name)
        with open(path, 'w') as f:
            json.dump(model_dict, f)
        return path
    
    def _has_riscv_assembler(self):
        """Check if RISC-V assembler is available."""
        try:
            result = subprocess.run(
                ['riscv64-elf-as', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def test_generated_assembly_is_valid_text(self):
        """Test that generated assembly is valid text."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        # Assembly file should be readable text
        with open(asm_path, 'r') as f:
            content = f.read()
        
        self.assertGreater(len(content), 0)
        self.assertIn("_start", content)
        self.assertIn(".section", content)
    
    def test_binary_file_created(self):
        """Test that binary file is created alongside assembly."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        bin_path = str(Path(asm_path).with_suffix('.bin'))
        self.assertTrue(os.path.exists(bin_path))
        self.assertGreater(os.path.getsize(bin_path), 0)
    
    def test_assembly_can_be_assembled(self):
        """Test that generated assembly can be assembled with RISC-V tools."""
        if not self._has_riscv_assembler():
            self.skipTest("RISC-V assembler not available")
        
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        # Try to assemble the generated .s file
        obj_path = str(Path(asm_path).with_suffix('.o'))
        result = subprocess.run(
            ['riscv64-elf-as', '-march=rv32if', '-mabi=ilp32f', asm_path, '-o', obj_path],
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed:\n{result.stderr.decode()}")
        self.assertTrue(os.path.exists(obj_path))
    
    def test_object_file_has_data_section(self):
        """Test that assembled object file has .data section."""
        if not self._has_riscv_assembler():
            self.skipTest("RISC-V assembler not available")
        
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        obj_path = str(Path(asm_path).with_suffix('.o'))
        result = subprocess.run(
            ['riscv64-elf-as', '-march=rv32if', '-mabi=ilp32f', asm_path, '-o', obj_path],
            capture_output=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        
        # Check that object file has .data section using objdump if available
        try:
            result = subprocess.run(
                ['riscv64-elf-objdump', '-h', obj_path],
                capture_output=True,
                timeout=10
            )
            output = result.stdout.decode()
            # Should have .data section
            self.assertIn('.data', output,
                        f"Object file missing .data section:\n{output}")
        except FileNotFoundError:
            # objdump not available, skip this check
            pass
    
    def test_object_file_has_text_section(self):
        """Test that assembled object file has .text section."""
        if not self._has_riscv_assembler():
            self.skipTest("RISC-V assembler not available")
        
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        obj_path = str(Path(asm_path).with_suffix('.o'))
        subprocess.run(
            ['riscv64-elf-as', '-march=rv32if', '-mabi=ilp32f', asm_path, '-o', obj_path],
            capture_output=True,
            timeout=10
        )
        
        # Check for .text section
        try:
            result = subprocess.run(
                ['riscv64-elf-objdump', '-h', obj_path],
                capture_output=True,
                timeout=10
            )
            output = result.stdout.decode()
            self.assertIn('.text', output,
                        f"Object file missing .text section:\n{output}")
        except FileNotFoundError:
            pass
    
    def test_incbin_binary_is_embedded(self):
        """Test that .incbin directive correctly embeds binary data."""
        if not self._has_riscv_assembler():
            self.skipTest("RISC-V assembler not available")
        
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        asm_result, bin_path = self.compiler.compile(json_path, asm_path)
        
        # Get binary file size
        bin_size = os.path.getsize(bin_path)
        
        # Assemble and check object file size
        obj_path = str(Path(asm_path).with_suffix('.o'))
        subprocess.run(
            ['riscv64-elf-as', '-march=rv32if', '-mabi=ilp32f', asm_path, '-o', obj_path],
            capture_output=True,
            timeout=10
        )
        
        # Object file should be larger than source (includes embedded binary)
        obj_size = os.path.getsize(obj_path)
        self.assertGreater(obj_size, bin_size,
                          f"Object file size ({obj_size}) not > binary size ({bin_size})")
    
    def test_assembly_syntax_valid(self):
        """Test that assembly follows valid RISC-V syntax."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        self.compiler.compile(json_path, asm_path)
        
        with open(asm_path, 'r') as f:
            content = f.read()
        
        # Check for required directives
        self.assertIn('.section', content)
        self.assertIn('.globl', content)
        self.assertIn('.align', content)
        
        # Check that labels exist
        self.assertIn('_start:', content)
        
        # Verify .incbin uses quoted path
        lines = content.split('\n')
        incbin_lines = [l for l in lines if '.incbin' in l and not l.strip().startswith('#')]
        self.assertEqual(len(incbin_lines), 1)
        self.assertIn('"', incbin_lines[0])
    
    def test_cli_interface(self):
        """Test command-line interface of model_compiler.py."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        # Run as command-line tool
        result = subprocess.run(
            ['python3', 'model_compiler.py', json_path, '-o', asm_path, '-v'],
            cwd=os.path.dirname(__file__) + '/..' or '.',
            capture_output=True,
            timeout=10
        )
        
        self.assertEqual(result.returncode, 0,
                        f"CLI failed:\n{result.stderr.decode()}")
        self.assertTrue(os.path.exists(asm_path))


if __name__ == '__main__':
    unittest.main()
