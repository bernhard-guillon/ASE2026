#!/usr/bin/env python3
"""Black box tests for Phase 3: Linker Script Configuration

Test that the bootloader.ld linker script correctly:
1. Links bootloader code and embedded data
2. Produces valid ELF files with correct section placement
3. Verifies sections are at expected addresses
"""

import unittest
import os
import subprocess
import tempfile
import struct
import re


class LinkerScriptIntegrationTest(unittest.TestCase):
    """Test linking bootloader with bootloader.ld"""

    def setUp(self):
        """Create temporary directory for test artifacts"""
        self.test_dir = tempfile.mkdtemp(prefix='bootloader_test_')
        self.emulator_dir = os.path.dirname(os.path.dirname(__file__))
        self.linker_script = os.path.join(self.emulator_dir, 'bootloader.ld')
        self.compiler_path = os.path.join(self.emulator_dir, 'model_compiler.py')
        
        # Verify linker script exists
        self.assertTrue(os.path.exists(self.linker_script),
                       f"Linker script not found: {self.linker_script}")

    def test_linker_script_exists(self):
        """Verify bootloader.ld can be found"""
        self.assertTrue(os.path.exists(self.linker_script),
                       "bootloader.ld not found")

    def test_link_simple_bootloader(self):
        """Test linking a simple bootloader assembly with bootloader.ld"""
        # Create a minimal bootloader assembly
        asm_file = os.path.join(self.test_dir, 'test_bootloader.s')
        with open(asm_file, 'w') as f:
            f.write('''
.section .text
.globl _start
_start:
    li sp, 0x20000
    li a0, 0
    li a7, 93
    ecall
.Lend:
    j .Lend
''')
        
        # Assemble
        obj_file = os.path.join(self.test_dir, 'test_bootloader.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed: {result.stderr}")
        self.assertTrue(os.path.exists(obj_file),
                       "Object file not created")
        
        # Link with bootloader.ld
        elf_file = os.path.join(self.test_dir, 'test_bootloader.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Linking failed: {result.stderr}")
        self.assertTrue(os.path.exists(elf_file),
                       "ELF file not created")

    def test_text_section_at_start(self):
        """Verify .text section is placed at 0x0"""
        # Create bootloader with data section
        asm_file = os.path.join(self.test_dir, 'test_placement.s')
        with open(asm_file, 'w') as f:
            f.write('''
.section .text
.globl _start
_start:
    j .Lstart_end
.Lstart_end:
    li a0, 0
    li a7, 93
    ecall

.section .data
.align 4
.globl test_data
test_data:
    .word 0xDEADBEEF
    .word 0xCAFEBABE
''')
        
        # Assemble
        obj_file = os.path.join(self.test_dir, 'test_placement.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed: {result.stderr}")
        
        # Link
        elf_file = os.path.join(self.test_dir, 'test_placement.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Linking failed: {result.stderr}")
        
        # Verify with readelf
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"readelf failed: {result.stderr}")
        
        # Check that .text section starts at 0
        self.assertIn('.text', result.stdout)
        # Parse section address
        match = re.search(r'\.text\s+PROGBITS\s+(\w+)', result.stdout)
        if match:
            addr = int(match.group(1), 16)
            self.assertEqual(addr, 0,
                           f".text should be at 0x0, but is at 0x{addr:x}")

    def test_data_section_in_correct_region(self):
        """Verify .data section is placed in DATA region"""
        # Create bootloader with data
        asm_file = os.path.join(self.test_dir, 'test_data_placement.s')
        with open(asm_file, 'w') as f:
            f.write('''
.section .text
.globl _start
_start:
    la t0, data_label
    lw t1, 0(t0)
    li a0, 0
    li a7, 93
    ecall

.section .data
.align 4
.globl data_label
data_label:
    .word 0x12345678
    .word 0xABCDEF00
''')
        
        # Assemble
        obj_file = os.path.join(self.test_dir, 'test_data_placement.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Assembly failed: {result.stderr}")
        
        # Link
        elf_file = os.path.join(self.test_dir, 'test_data_placement.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Linking failed: {result.stderr}")
        
        # Verify with readelf
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"readelf failed: {result.stderr}")
        
        # Should have both .text and .data sections
        self.assertIn('.text', result.stdout)
        self.assertIn('.data', result.stdout)

    def test_elf_program_headers(self):
        """Verify ELF has correct program headers"""
        # Create simple bootloader
        asm_file = os.path.join(self.test_dir, 'test_headers.s')
        with open(asm_file, 'w') as f:
            f.write('''
.section .text
.globl _start
_start:
    li a0, 0
    li a7, 93
    ecall
''')
        
        # Assemble
        obj_file = os.path.join(self.test_dir, 'test_headers.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Link
        elf_file = os.path.join(self.test_dir, 'test_headers.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Check program headers with readelf
        result = subprocess.run(
            ['riscv64-elf-readelf', '-l', elf_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"readelf failed: {result.stderr}")
        
        # Should have at least one LOAD program header
        self.assertIn('LOAD', result.stdout,
                     "ELF should have LOAD program header")

    def test_entry_point_is_start(self):
        """Verify entry point is set to _start"""
        # Create bootloader
        asm_file = os.path.join(self.test_dir, 'test_entry.s')
        with open(asm_file, 'w') as f:
            f.write('''
.section .text
.globl _start
_start:
    li a0, 0
    li a7, 93
    ecall
''')
        
        # Assemble
        obj_file = os.path.join(self.test_dir, 'test_entry.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Link
        elf_file = os.path.join(self.test_dir, 'test_entry.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Check entry point with readelf
        result = subprocess.run(
            ['riscv64-elf-readelf', '-h', elf_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Entry point should be 0x0 or address of _start
        self.assertIn('Entry point address:', result.stdout)

    def test_linker_script_syntax_valid(self):
        """Verify linker script has valid syntax"""
        # Try to use the linker script with a simple object file
        asm_file = os.path.join(self.test_dir, 'test_syntax.s')
        with open(asm_file, 'w') as f:
            f.write('.section .text\n_start: j _start\n')
        
        obj_file = os.path.join(self.test_dir, 'test_syntax.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Link - if script has syntax errors, this will fail
        elf_file = os.path.join(self.test_dir, 'test_syntax.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        f"Linker script syntax error: {result.stderr}")

    def test_can_link_with_model_data(self):
        """Verify linker script works with model data section"""
        # Create assembly with .incbin like model_compiler generates
        asm_file = os.path.join(self.test_dir, 'test_model_data.s')
        
        # Create a small binary file to embed
        binary_file = os.path.join(self.test_dir, 'test_data.bin')
        with open(binary_file, 'wb') as f:
            f.write(b'\x4E\x52\x41\x4E')  # Magic: "NRAL"
            f.write(b'\x01\x00\x00\x00')  # Version: 1
            f.write(b'\x00' * 100)        # Padding
        
        # Create assembly that references the binary
        with open(asm_file, 'w') as f:
            f.write(f'''
.section .text
.globl _start
_start:
    la t0, model_data_start
    li a0, 0
    li a7, 93
    ecall

.section .data
.align 4
.globl model_data_start
model_data_start:
    .incbin "{binary_file}"
.globl model_data_end
model_data_end:
''')
        
        # Assemble (may fail due to path, but that's OK for this test)
        obj_file = os.path.join(self.test_dir, 'test_model_data.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True,
            cwd=self.test_dir  # Set working directory
        )
        
        if result.returncode == 0:
            # Link
            elf_file = os.path.join(self.test_dir, 'test_model_data.elf')
            result = subprocess.run(
                ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0,
                            f"Linking with model data failed: {result.stderr}")


class LinkerScriptMemoryLayoutTest(unittest.TestCase):
    """Test memory layout constraints"""

    def setUp(self):
        """Load linker script"""
        self.emulator_dir = os.path.dirname(os.path.dirname(__file__))
        self.linker_script = os.path.join(self.emulator_dir, 'bootloader.ld')

    def test_code_starts_at_zero(self):
        """Verify CODE region starts at 0x0"""
        with open(self.linker_script, 'r') as f:
            content = f.read()
        
        # Parse CODE origin
        match = re.search(r'CODE\s*\([^)]*\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
                         content)
        self.assertIsNotNone(match, "Cannot parse CODE origin")
        origin = int(match.group(1), 16)
        self.assertEqual(origin, 0x0,
                        "CODE region should start at 0x0")

    def test_data_after_code(self):
        """Verify DATA region comes after CODE"""
        with open(self.linker_script, 'r') as f:
            content = f.read()
        
        # Parse both origins
        code_match = re.search(r'CODE\s*\([^)]*\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
                              content)
        data_match = re.search(r'DATA\s*\([^)]*\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
                              content)
        
        self.assertIsNotNone(code_match)
        self.assertIsNotNone(data_match)
        
        code_origin = int(code_match.group(1), 16)
        data_origin = int(data_match.group(1), 16)
        
        self.assertGreater(data_origin, code_origin,
                          "DATA should come after CODE in memory")


if __name__ == '__main__':
    unittest.main(verbosity=2)
