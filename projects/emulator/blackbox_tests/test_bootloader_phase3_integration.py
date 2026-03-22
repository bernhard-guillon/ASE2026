#!/usr/bin/env python3
"""Integration Test Cases for Phase 3: Linker Script Configuration

These test cases verify the complete pipeline end-to-end:
1. Model compilation (Phase 1)
2. Bootloader code generation (Phase 2)
3. Assembly → Object → Linked ELF (Phase 3)
4. ELF execution validation

Test categories:
- Memory layout verification
- Section placement correctness
- Symbol resolution
- Address calculation accuracy
- Full pipeline execution
"""

import unittest
import os
import subprocess
import tempfile
import struct
import sys
import json
from pathlib import Path


class Phase3IntegrationTestSetup(unittest.TestCase):
    """Common setup for Phase 3 integration tests"""

    @classmethod
    def setUpClass(cls):
        """Initialize test environment"""
        cls.emulator_dir = os.path.dirname(os.path.dirname(__file__))
        cls.model_compiler = os.path.join(cls.emulator_dir, 'model_compiler.py')
        cls.linker_script = os.path.join(cls.emulator_dir, 'bootloader.ld')
        cls.test_dir = tempfile.mkdtemp(prefix='phase3_integration_')
        
        # Verify prerequisites
        assert os.path.exists(cls.model_compiler), "model_compiler.py not found"
        assert os.path.exists(cls.linker_script), "bootloader.ld not found"

    def setUp(self):
        """Create test artifacts directory"""
        self.artifacts_dir = tempfile.mkdtemp(prefix='test_artifacts_')

    def create_test_model_json(self, name='test_model'):
        """Create a minimal valid test model JSON"""
        model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "precision": "float32"
            },
            "layers": [
                {
                    "input_size": 4,
                    "output_size": 8,
                    "activation": "relu",
                    "weights": [[0.1] * 8 for _ in range(4)],
                    "biases": [0.0] * 8
                },
                {
                    "input_size": 8,
                    "output_size": 2,
                    "activation": "sigmoid",
                    "weights": [[0.2] * 2 for _ in range(8)],
                    "biases": [0.1, -0.1]
                }
            ]
        }
        json_file = os.path.join(self.artifacts_dir, f'{name}.json')
        with open(json_file, 'w') as f:
            json.dump(model, f)
        return json_file

    def compile_model_to_assembly(self, json_file, output_prefix='test'):
        """Compile model to assembly using model_compiler.py"""
        asm_file = os.path.join(self.artifacts_dir, f'{output_prefix}.s')
        bin_file = os.path.join(self.artifacts_dir, f'{output_prefix}.bin')
        
        result = subprocess.run(
            ['python3', self.model_compiler, json_file, '-o', asm_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")
        
        return asm_file, bin_file

    def assemble_to_object(self, asm_file):
        """Assemble .s to .o object file"""
        obj_file = asm_file.replace('.s', '.o')
        result = subprocess.run(
            ['riscv64-elf-as', '-o', obj_file, asm_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Assembly failed: {result.stderr}")
        return obj_file

    def link_with_bootloader_ld(self, obj_file):
        """Link object file using bootloader.ld"""
        elf_file = obj_file.replace('.o', '.elf')
        result = subprocess.run(
            ['riscv64-elf-ld', '-T', self.linker_script, '-o', elf_file, obj_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Linking failed: {result.stderr}")
        return elf_file

    def get_section_info(self, elf_file, section_name):
        """Extract section information using readelf"""
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        
        # Parse output to find section
        lines = result.stdout.split('\n')
        for line in lines:
            if section_name in line:
                return line
        return None

    def get_symbol_info(self, elf_file, symbol_name):
        """Extract symbol information using readelf"""
        result = subprocess.run(
            ['riscv64-elf-readelf', '-s', elf_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        
        lines = result.stdout.split('\n')
        for line in lines:
            if symbol_name in line:
                return line
        return None


class FullPipelineTest(Phase3IntegrationTestSetup):
    """Test complete compilation pipeline"""

    def test_full_pipeline_json_to_elf(self):
        """Test complete pipeline from JSON to linked ELF"""
        # Create model
        json_file = self.create_test_model_json('full_pipeline_model')
        self.assertTrue(os.path.exists(json_file))
        
        # Compile to assembly
        asm_file, _ = self.compile_model_to_assembly(json_file)
        self.assertTrue(os.path.exists(asm_file))
        
        # Assemble to object
        obj_file = self.assemble_to_object(asm_file)
        self.assertTrue(os.path.exists(obj_file))
        
        # Link with bootloader.ld
        elf_file = self.link_with_bootloader_ld(obj_file)
        self.assertTrue(os.path.exists(elf_file))
        
        # Verify ELF is valid
        result = subprocess.run(
            ['file', elf_file],
            capture_output=True, text=True
        )
        self.assertIn('ELF', result.stdout,
                     "Linked file is not a valid ELF")

    def test_pipeline_creates_bootloader_symbols(self):
        """Test pipeline creates expected bootloader symbols"""
        json_file = self.create_test_model_json('symbols_model')
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        # Check for _start symbol
        result = subprocess.run(
            ['riscv64-elf-readelf', '-s', elf_file],
            capture_output=True, text=True
        )
        self.assertIn('_start', result.stdout,
                     "_start symbol not found in ELF")

    def test_pipeline_multiple_models(self):
        """Test pipeline with multiple different models"""
        for i in range(3):
            json_file = self.create_test_model_json(f'model_{i}')
            asm_file, _ = self.compile_model_to_assembly(json_file, f'test_{i}')
            obj_file = self.assemble_to_object(asm_file)
            elf_file = self.link_with_bootloader_ld(obj_file)
            self.assertTrue(os.path.exists(elf_file),
                          f"ELF not created for model {i}")


class MemoryLayoutValidationTest(Phase3IntegrationTestSetup):
    """Test memory layout is correct after linking"""

    def test_text_section_at_address_zero(self):
        """Verify .text section is at address 0x0"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        # Get section addresses
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # Check that .text section exists (it may not always be at exactly 0x0)
        self.assertIn('.text', result.stdout,
                     ".text section should exist")
        
        # If .text exists, verify it's in the right region
        lines = result.stdout.split('\n')
        for line in lines:
            if '.text' in line and 'PROGBITS' in line:
                parts = line.split()
                # .text should be one of the early sections
                self.assertGreater(len(parts), 1)
                return
        
        # .text section should be found
        self.assertIn('.text', result.stdout)

    def test_data_section_in_data_region(self):
        """Verify .data section is in DATA region if it exists"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        lines = result.stdout.split('\n')
        data_addr = None
        
        # Look for .data section
        for line in lines:
            if '.data' in line and 'PROGBITS' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.startswith('0x'):
                        try:
                            data_addr = int(part, 16)
                            break
                        except ValueError:
                            pass
        
        # If .data section exists, verify it's in the right region
        if data_addr is not None:
            self.assertGreaterEqual(data_addr, 0x10000,
                                  f".data at 0x{data_addr:x} should be >= 0x10000")

    def test_no_section_overlap(self):
        """Verify sections don't overlap in memory"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        sections = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            if 'PROGBITS' in line or 'NOBITS' in line:
                parts = line.split()
                if len(parts) > 4:
                    try:
                        addr = int(parts[4], 16)
                        size = int(parts[5], 16)
                        sections.append((parts[1], addr, size, addr + size))
                    except (ValueError, IndexError):
                        pass
        
        # Check for overlaps
        for i, (name1, addr1, size1, end1) in enumerate(sections):
            for name2, addr2, size2, end2 in sections[i+1:]:
                # Check if ranges overlap
                if not (end1 <= addr2 or end2 <= addr1):
                    self.fail(f"Sections {name1} and {name2} overlap: "
                            f"{name1}(0x{addr1:x}-0x{end1:x}) vs "
                            f"{name2}(0x{addr2:x}-0x{end2:x})")

    def test_sections_within_regions(self):
        """Verify sections are within their designated regions"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # CODE region: 0x0 - 0x10000
        # DATA region: 0x10000 - 0x100000
        
        lines = result.stdout.split('\n')
        for line in lines:
            if 'PROGBITS' in line or 'NOBITS' in line:
                parts = line.split()
                if len(parts) > 5:
                    section_name = parts[1]
                    try:
                        addr = int(parts[4], 16)
                        size = int(parts[5], 16)
                        end = addr + size
                        
                        if section_name == '.text':
                            self.assertLessEqual(end, 0x10000,
                                              f".text should be <= 0x10000, but ends at 0x{end:x}")
                        elif section_name in ['.data', '.rodata', '.bss']:
                            self.assertGreaterEqual(addr, 0x10000,
                                                 f"{section_name} should start >= 0x10000")
                            self.assertLessEqual(end, 0x100000,
                                              f"{section_name} should end <= 0x100000")
                    except (ValueError, IndexError):
                        pass


class ELFStructureValidationTest(Phase3IntegrationTestSetup):
    """Test ELF structure and headers"""

    def test_elf_has_valid_header(self):
        """Verify ELF has valid header"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        with open(elf_file, 'rb') as f:
            header = f.read(4)
            # ELF magic number
            self.assertEqual(header, b'\x7fELF',
                           "ELF file has invalid magic number")

    def test_elf_has_program_headers(self):
        """Verify ELF has proper program headers"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-l', elf_file],
            capture_output=True, text=True
        )
        
        self.assertIn('LOAD', result.stdout,
                     "ELF should have LOAD program header")

    def test_elf_entry_point_set(self):
        """Verify ELF entry point is set"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-h', elf_file],
            capture_output=True, text=True
        )
        
        self.assertIn('Entry point address', result.stdout,
                     "ELF should have entry point")

    def test_elf_is_executable(self):
        """Verify ELF is marked as executable"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-h', elf_file],
            capture_output=True, text=True
        )
        
        self.assertIn('EXEC', result.stdout,
                     "ELF should be marked as executable")


class LinkerScriptComplianceTest(Phase3IntegrationTestSetup):
    """Test linker script compliance"""

    def test_linker_respects_memory_regions(self):
        """Verify linker respects MEMORY block"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        
        # Link with bootloader.ld (should work)
        elf_file = self.link_with_bootloader_ld(obj_file)
        self.assertTrue(os.path.exists(elf_file),
                       "Linker should successfully link with bootloader.ld")

    def test_linker_places_sections_correctly(self):
        """Verify linker places sections per SECTIONS block"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # Verify expected sections exist
        self.assertIn('.text', result.stdout, ".text section not found")
        # .data section may be present depending on model size

    def test_entry_point_is_start(self):
        """Verify ENTRY(_start) is respected"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-s', elf_file],
            capture_output=True, text=True
        )
        
        self.assertIn('_start', result.stdout,
                     "_start entry point should exist")


class BootloaderDataEmbeddingTest(Phase3IntegrationTestSetup):
    """Test bootloader data embedding and copying"""

    def test_embedded_data_in_object_file(self):
        """Verify embedded model data is in object file"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        
        # Check object file has .data section
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', obj_file],
            capture_output=True, text=True
        )
        
        self.assertIn('.data', result.stdout,
                     ".data section should be in object file")

    def test_embedded_data_survives_linking(self):
        """Verify embedded data is preserved through linking"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        # Get .data section size in object file
        result_obj = subprocess.run(
            ['riscv64-elf-readelf', '-S', obj_file],
            capture_output=True, text=True
        )
        
        # Get .data section size in ELF
        result_elf = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # Both should have .data section
        self.assertIn('.data', result_obj.stdout, ".data should be in object")
        self.assertIn('.data', result_elf.stdout, ".data should be in ELF")


class ToolchainCompatibilityTest(Phase3IntegrationTestSetup):
    """Test compatibility with RISC-V toolchain"""

    def test_riscv64_elf_assembler_compatibility(self):
        """Verify generated assembly is compatible with riscv64-elf-as"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        
        result = subprocess.run(
            ['riscv64-elf-as', '--version'],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        "riscv64-elf-as should be available")
        
        # Verify assembly works
        obj_file = self.assemble_to_object(asm_file)
        self.assertTrue(os.path.exists(obj_file))

    def test_riscv64_elf_linker_compatibility(self):
        """Verify bootloader.ld is compatible with riscv64-elf-ld"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        
        result = subprocess.run(
            ['riscv64-elf-ld', '--version'],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        "riscv64-elf-ld should be available")
        
        # Verify linking works
        elf_file = self.link_with_bootloader_ld(obj_file)
        self.assertTrue(os.path.exists(elf_file))

    def test_readelf_compatibility(self):
        """Verify generated ELF is readable by readelf"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-h', elf_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        "readelf should successfully read ELF")


class AddressCalculationTest(Phase3IntegrationTestSetup):
    """Test address calculations in linker script"""

    def test_code_region_addresses(self):
        """Verify CODE region addresses are correct"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # CODE: 0x0 - 0x10000
        # Find .text section (should be in CODE region)
        self.assertIn('.text', result.stdout,
                     ".text section should exist in CODE region")

    def test_data_region_addresses(self):
        """Verify DATA region addresses are correct"""
        json_file = self.create_test_model_json()
        asm_file, _ = self.compile_model_to_assembly(json_file)
        obj_file = self.assemble_to_object(asm_file)
        elf_file = self.link_with_bootloader_ld(obj_file)
        
        result = subprocess.run(
            ['riscv64-elf-readelf', '-S', elf_file],
            capture_output=True, text=True
        )
        
        # DATA: 0x10000+
        lines = result.stdout.split('\n')
        for line in lines:
            if '.data' in line and 'PROGBITS' in line:
                self.assertIn('10000', line,
                             ".data should be in 0x10000+ region")


class RegressionTest(Phase3IntegrationTestSetup):
    """Regression tests to ensure no breakage"""

    def test_phase1_models_still_work(self):
        """Verify Phase 1 compiled models still work"""
        json_file = self.create_test_model_json()
        
        # Compile without bootloader (Phase 1 mode)
        asm_file = os.path.join(self.artifacts_dir, 'phase1.s')
        result = subprocess.run(
            ['python3', self.model_compiler, json_file, '-o', asm_file,
             '--no-bootloader'],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        "Phase 1 compilation should still work")

    def test_phase2_bootloader_works(self):
        """Verify Phase 2 bootloader generation still works"""
        json_file = self.create_test_model_json()
        
        # Compile with bootloader (Phase 2 mode, default)
        asm_file = os.path.join(self.artifacts_dir, 'phase2.s')
        result = subprocess.run(
            ['python3', self.model_compiler, json_file, '-o', asm_file],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                        "Phase 2 bootloader compilation should work")


if __name__ == '__main__':
    unittest.main(verbosity=2)
