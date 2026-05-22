#!/usr/bin/env python3
"""
Unit tests for Phase 2: Bootloader Code Generation.

Tests verify:
1. Bootloader code generation produces valid assembly
2. Memory initialization code is correctly generated
3. Address calculations for model loading
4. Size calculations match binary data
5. Stack initialization code
6. Exit syscall generation
7. Loop structure for memcpy-like operations
"""

import unittest
import tempfile
import json
import subprocess
import os
from pathlib import Path
from model_compiler import ModelCompiler


class TestBootloaderCodeGeneration(unittest.TestCase):
    """Test cases for Phase 2: Bootloader code generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.compiler = ModelCompiler(verbose=False)
        
        # Generator model for testing
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
                    "input_size": 8,
                    "output_size": 4,
                    "activation": "relu",
                    "weights_shape": [8, 4],
                    "weights": [[float(i*4+j) for j in range(4)] for i in range(8)],
                    "biases_shape": [4],
                    "biases": [float(i) * 0.1 for i in range(4)]
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
    
    def test_bootloader_assembly_contains_stack_init(self):
        """Test that bootloader initializes stack pointer."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have stack pointer initialization
        self.assertIn("lui sp", asm_content)
        self.assertIn("0x20", asm_content)  # Stack at 0x20000
    
    def test_bootloader_assembly_has_copy_loop(self):
        """Test that bootloader has memcpy-like copy loop."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have copy loop
        self.assertIn(".Lcopy_loop", asm_content)
        self.assertIn("lbu", asm_content)   # Load byte unsigned
        self.assertIn("sb", asm_content)    # Store byte
        self.assertIn("bge", asm_content)   # Branch if greater or equal
    
    def test_bootloader_assembly_has_exit_syscall(self):
        """Test that bootloader exits with syscall."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have exit syscall
        self.assertIn("li a7, 93", asm_content)  # SYS_exit = 93
        self.assertIn("ecall", asm_content)
        self.assertIn("li a0, 0", asm_content)   # exit code 0
    
    def test_bootloader_includes_verification(self):
        """Test that bootloader includes verification routine."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have verification routine
        self.assertIn("verify_model", asm_content)
        self.assertIn(".Lverify_fail", asm_content)
        self.assertIn(".Lverify_done", asm_content)
    
    def test_bootloader_verifies_magic_number(self):
        """Test that bootloader verifies magic number."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should check magic number 0x4E52414E ("NRAL")
        self.assertIn("0x4E52414E", asm_content)
        self.assertIn("magic", asm_content.lower())
    
    def test_bootloader_verifies_version(self):
        """Test that bootloader verifies version number."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should check version = 1
        self.assertIn("version", asm_content.lower())
        # Load at offset 4 (version field)
        self.assertIn("4(a5)", asm_content)
    
    def test_generator_model_destination_address(self):
        """Test that generator model uses correct destination address."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Generator should load to 0x10000
        self.assertIn("0x10", asm_content)  # lui 0x10 for 0x10000
    
    def test_bootloader_loads_correct_size(self):
        """Test that bootloader copies correct number of bytes."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        # Compile and check binary size
        asm_result, bin_result = self.compiler.compile(json_path, asm_path, 
                                                       with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have size in li instruction
        with open(bin_result, 'rb') as f:
            bin_size = len(f.read())
        
        # Bootloader should reference this size
        self.assertIn(f"li a2, {bin_size}", asm_content)
    
    def test_bootloader_assembles_successfully(self):
        """Test that bootloader assembly can be assembled."""
        if subprocess.run(['which', 'riscv64-elf-as'],
                         capture_output=True).returncode != 0:
            self.skipTest("RISC-V assembler not available")
        
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        obj_path = str(Path(asm_path).with_suffix('.o'))
        result = subprocess.run(
            ['riscv64-elf-as', '-march=rv32i', asm_path, '-o', obj_path],
            capture_output=True
        )
        
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed:\n{result.stderr.decode()}")
    
    def test_bootloader_has_la_directive(self):
        """Test that bootloader uses 'la' pseudo-instruction for model_data_start."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should load address of model_data_start
        self.assertIn("la a0, model_data_start", asm_content)
    
    def test_bootloader_loop_counter(self):
        """Test that bootloader has proper loop counter management."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should initialize counter (a3 = 0)
        self.assertIn("xor a3, a3, a3", asm_content)
        # Should increment counter
        self.assertIn("addi a3, a3, 1", asm_content)
    
    def test_bootloader_uses_registers_correctly(self):
        """Test that bootloader uses registers according to RV32I ABI."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # a0: source address / exit code
        # a1: destination address
        # a2: size
        # a3: loop counter
        # a4, a5: temporary registers
        
        self.assertIn("a0", asm_content)
        self.assertIn("a1", asm_content)
        self.assertIn("a2", asm_content)
        self.assertIn("a3", asm_content)
    
    def test_skeleton_mode_disables_bootloader(self):
        """Test that --no-bootloader flag generates skeleton only."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=False)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should NOT have copy loop (skeleton mode)
        self.assertNotIn(".Lcopy_loop", asm_content)
        # Should have placeholder
        self.assertIn("j _start", asm_content)
    
    def test_bootloader_vs_skeleton_difference(self):
        """Test clear difference between bootloader and skeleton modes."""
        json_path = self._save_json(self.gen_model)
        
        # Generate with bootloader
        asm_boot = os.path.join(self.temp_dir.name, "boot.s")
        self.compiler.compile(json_path, asm_boot, with_bootloader=True)
        with open(asm_boot, 'r') as f:
            boot_content = f.read()
        
        # Generate without bootloader
        asm_skel = os.path.join(self.temp_dir.name, "skel.s")
        self.compiler.compile(json_path, asm_skel, with_bootloader=False)
        with open(asm_skel, 'r') as f:
            skel_content = f.read()
        
        # Bootloader should have copy loop
        self.assertIn(".Lcopy_loop", boot_content)
        self.assertNotIn(".Lcopy_loop", skel_content)
        
        # Bootloader should have verification
        self.assertIn("verify_model", boot_content)
        self.assertNotIn("verify_model", skel_content)
        
        # Bootloader should have stack init (lui sp)
        self.assertIn("lui sp", boot_content)
        
        # Skeleton should not have stack init
        self.assertNotIn("lui sp", skel_content)
        
        # Skeleton should be much shorter
        self.assertGreater(len(boot_content), len(skel_content) * 2)
    
    def test_verification_exit_codes(self):
        """Test that verification uses different exit codes."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should have success exit code (0)
        self.assertIn("li a0, 0", asm_content)
        # Should have failure exit code (1)
        self.assertIn("li a0, 1", asm_content)
        # Should branch on verification result
        self.assertIn(".Lverify_failed", asm_content)
    
    def test_verification_samples_data_section(self):
        """Test that verification samples different parts of data section."""
        json_path = self._save_json(self.gen_model)
        asm_path = os.path.join(self.temp_dir.name, "boot.s")
        
        self.compiler.compile(json_path, asm_path, with_bootloader=True)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Should verify header, layer table, first/middle/last data
        self.assertIn("Verify Layer Table", asm_content)
        self.assertIn("Verify Data Integrity", asm_content)
        self.assertIn("first data", asm_content.lower())
        self.assertIn("middle data", asm_content.lower())
        self.assertIn("end data", asm_content.lower())


if __name__ == '__main__':
    unittest.main()
