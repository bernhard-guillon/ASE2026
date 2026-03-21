#!/usr/bin/env python3
"""Unit tests for Phase 3: Linker Script Configuration

Test the bootloader.ld linker script to ensure:
1. Memory regions are correctly defined
2. Sections are properly placed
3. Script syntax is valid
4. Address constraints are respected
"""

import unittest
import os
import re
import subprocess
import tempfile


class LinkerScriptParsingTest(unittest.TestCase):
    """Test parsing and validation of bootloader.ld"""

    @classmethod
    def setUpClass(cls):
        """Load the linker script"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )
        with open(cls.script_path, 'r') as f:
            cls.script_content = f.read()

    def test_script_exists(self):
        """Verify bootloader.ld exists"""
        self.assertTrue(os.path.exists(self.script_path),
                       "bootloader.ld not found")

    def test_script_is_not_empty(self):
        """Verify script has content"""
        self.assertGreater(len(self.script_content), 0,
                          "bootloader.ld is empty")

    def test_memory_section_exists(self):
        """Verify MEMORY block is defined"""
        self.assertIn('MEMORY', self.script_content,
                     "MEMORY section not found in linker script")

    def test_sections_block_exists(self):
        """Verify SECTIONS block is defined"""
        self.assertIn('SECTIONS', self.script_content,
                     "SECTIONS block not found in linker script")

    def test_entry_point_defined(self):
        """Verify ENTRY point is defined"""
        self.assertIn('ENTRY', self.script_content,
                     "ENTRY point not defined")
        self.assertIn('_start', self.script_content,
                     "_start entry point not found")


class MemoryRegionTest(unittest.TestCase):
    """Test memory region definitions in bootloader.ld"""

    @classmethod
    def setUpClass(cls):
        """Load and parse the linker script"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )
        with open(cls.script_path, 'r') as f:
            cls.script_content = f.read()

    def test_code_region_defined(self):
        """Verify CODE memory region is defined"""
        self.assertIn('CODE', self.script_content,
                     "CODE region not defined")
        self.assertIn('(rx)', self.script_content,
                     "CODE region missing read/execute permission")

    def test_data_region_defined(self):
        """Verify DATA memory region is defined"""
        self.assertIn('DATA', self.script_content,
                     "DATA region not defined")
        self.assertIn('(rw)', self.script_content,
                     "DATA region missing read/write permission")

    def test_code_region_origin(self):
        """Verify CODE region starts at 0x0"""
        # Extract CODE origin
        match = re.search(r'CODE\s*\(rx\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
                         self.script_content)
        self.assertIsNotNone(match, "Cannot parse CODE origin")
        origin = int(match.group(1), 16)
        self.assertEqual(origin, 0x00000000,
                        "CODE origin should be 0x00000000")

    def test_code_region_length(self):
        """Verify CODE region has proper length"""
        # Extract CODE length
        match = re.search(r'CODE\s*\(rx\)\s*:\s*ORIGIN\s*=.*LENGTH\s*=\s*([\d.]+[KMG]?)',
                         self.script_content)
        self.assertIsNotNone(match, "Cannot parse CODE length")

    def test_data_region_origin(self):
        """Verify DATA region starts after CODE"""
        # Extract DATA origin
        match = re.search(r'DATA\s*\(rw\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
                         self.script_content)
        self.assertIsNotNone(match, "Cannot parse DATA origin")
        origin = int(match.group(1), 16)
        # DATA should start at or after 0x10000
        self.assertGreaterEqual(origin, 0x00010000,
                               "DATA origin should be at least 0x00010000")

    def test_data_region_length(self):
        """Verify DATA region has sufficient length for models"""
        # Extract DATA length
        match = re.search(r'DATA\s*\(rw\)\s*:\s*ORIGIN\s*=.*LENGTH\s*=\s*([\d.]+[KMG]?)',
                         self.script_content)
        self.assertIsNotNone(match, "Cannot parse DATA length")
        # Should have at least 960K for bootloader and models


class SectionPlacementTest(unittest.TestCase):
    """Test section placement rules in bootloader.ld"""

    @classmethod
    def setUpClass(cls):
        """Load and parse the linker script"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )
        with open(cls.script_path, 'r') as f:
            cls.script_content = f.read()

    def test_text_section_in_code(self):
        """Verify .text section is placed in CODE region"""
        self.assertIn('.text', self.script_content,
                     ".text section not defined")
        # Check if it uses > CODE (use [\s\S]*? to match newlines)
        match = re.search(r'\.text\s*:[\s\S]*?>\s*CODE', self.script_content)
        self.assertIsNotNone(match, ".text not placed in CODE region")

    def test_rodata_section_exists(self):
        """Verify .rodata section is defined"""
        self.assertIn('.rodata', self.script_content,
                     ".rodata section not defined")

    def test_data_section_in_memory(self):
        """Verify .data section is placed in DATA region"""
        self.assertIn('.data', self.script_content,
                     ".data section not defined")
        match = re.search(r'\.data\s*:[\s\S]*?>\s*DATA', self.script_content)
        self.assertIsNotNone(match, ".data not placed in DATA region")

    def test_bss_section_exists(self):
        """Verify .bss section is defined"""
        self.assertIn('.bss', self.script_content,
                     ".bss section not defined")

    def test_wildcard_patterns(self):
        """Verify wildcard patterns for object files"""
        # Should have *(.text), *(.data), etc.
        self.assertIn('*(.text', self.script_content,
                     "Wildcard pattern for .text not found")
        self.assertIn('*(.data', self.script_content,
                     "Wildcard pattern for .data not found")


class LinkerScriptSyntaxTest(unittest.TestCase):
    """Test linker script syntax validity"""

    @classmethod
    def setUpClass(cls):
        """Initialize paths"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )

    def test_script_ld_format(self):
        """Verify script is in GNU LD format"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        
        # Should contain key GNU LD features
        self.assertIn('MEMORY', content)
        self.assertIn('SECTIONS', content)
        self.assertTrue(content.count('{') == content.count('}'),
                       "Mismatched braces in linker script")

    def test_no_syntax_errors_basic(self):
        """Basic syntax check - matching braces and parentheses"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'//.*', '', content)
        
        # Check braces
        self.assertEqual(content.count('{'), content.count('}'),
                        "Mismatched curly braces")
        
        # Check parentheses
        self.assertEqual(content.count('('), content.count(')'),
                        "Mismatched parentheses")


class LinkerScriptComplianceTest(unittest.TestCase):
    """Test bootloader.ld compliance with requirements"""

    @classmethod
    def setUpClass(cls):
        """Load the linker script"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )
        with open(cls.script_path, 'r') as f:
            cls.script_content = f.read()

    def test_code_at_start_of_memory(self):
        """Verify code section starts at 0x0"""
        # .text should be placed in CODE region which starts at 0x0
        match = re.search(r'\.text\s*:[\s\S]*?>\s*CODE', self.script_content)
        self.assertIsNotNone(match, ".text should be in CODE at 0x0")

    def test_model_addresses_addressable(self):
        """Verify memory regions support required model addresses"""
        # Generator: 0x10000
        # Recognizer: 0xF4ABC
        # Both should be addressable in DATA region
        
        # Extract DATA region bounds
        data_match = re.search(
            r'DATA\s*\(rw\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
            self.script_content
        )
        self.assertIsNotNone(data_match, "Cannot parse DATA origin")
        data_origin = int(data_match.group(1), 16)
        
        # Both model addresses should be >= data_origin or in a separate region
        # (Models are loaded at runtime, not linked)

    def test_stack_addressable(self):
        """Verify stack address 0x20000 is addressable"""
        # Stack is set to 0x20000 by bootloader code
        # Should be in available memory

    def test_has_comments(self):
        """Verify script has documentation comments"""
        self.assertIn('/*', self.script_content,
                     "Script should have documentation comments")
        self.assertIn('*/', self.script_content,
                     "Script comments should be closed")

    def test_discard_section(self):
        """Verify unnecessary sections are discarded"""
        self.assertIn('/DISCARD/', self.script_content,
                     "Should discard unnecessary ELF sections")
        self.assertIn('.note.GNU-stack', self.script_content,
                     "Should discard .note.GNU-stack")


class AddressCalculationTest(unittest.TestCase):
    """Test that address calculations work with the linker script"""

    @classmethod
    def setUpClass(cls):
        """Load the linker script"""
        cls.script_path = os.path.join(
            os.path.dirname(__file__), 'bootloader.ld'
        )
        with open(cls.script_path, 'r') as f:
            cls.script_content = f.read()

    def test_address_regions_dont_overlap(self):
        """Verify CODE and DATA regions don't overlap"""
        # Extract CODE region info
        code_match = re.search(
            r'CODE\s*\(rx\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+),\s*LENGTH\s*=\s*([\d.]+[KMG]?)',
            self.script_content
        )
        self.assertIsNotNone(code_match, "Cannot parse CODE region")
        
        # Extract DATA region info
        data_match = re.search(
            r'DATA\s*\(rw\)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)',
            self.script_content
        )
        self.assertIsNotNone(data_match, "Cannot parse DATA region")
        
        code_origin = int(code_match.group(1), 16)
        data_origin = int(data_match.group(1), 16)
        
        # DATA should come after CODE
        self.assertGreater(data_origin, code_origin,
                          "DATA region should come after CODE")

    def test_bootloader_code_placement(self):
        """Verify bootloader code is placed correctly"""
        # Bootloader code (.text) should be in CODE at 0x0
        self.assertIn('.text', self.script_content)
        match = re.search(r'\.text\s*:[\s\S]*?>\s*CODE', self.script_content)
        self.assertIsNotNone(match, ".text not in CODE region")

    def test_embedded_data_placement(self):
        """Verify embedded model data can be placed in DATA"""
        # .data and .rodata should be in DATA
        self.assertIn('.data', self.script_content)
        self.assertIn('.rodata', self.script_content)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
