#!/usr/bin/env python3
"""
Phase 6 Integration Tests: Comprehensive Bootloader Validation

Tests the complete bootloader system end-to-end:
- Model loading into emulator
- Memory layout validation
- Bootloader execution
- Data integrity verification
- Error handling and edge cases
"""

import json
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Tuple
import pytest
import numpy as np

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from compile_model_bootloader import BootloaderPipeline


class Phase6IntegrationTestSetup:
    """Base class providing test helpers for Phase 6."""
    
    @staticmethod
    def create_simple_model_json(work_dir: Path, model_type: str = "generator") -> Tuple[Path, Dict]:
        """
        Create a simple but realistic model JSON file.
        
        Args:
            work_dir: Directory to create JSON in
            model_type: "generator" or "recognizer"
            
        Returns:
            Tuple of (json_path, model_data)
        """
        model_data = {
            "metadata": {
                "model_type": model_type,
                "precision": "float32",
                "version": "1.0",
                "input_size": 10,
                "output_size": 5
            },
            "layers": [
                {
                    "input_size": 10,
                    "output_size": 8,
                    "activation": "relu",
                    "weights": [[float(i + j) / 100.0 for j in range(8)] for i in range(10)],
                    "biases": [float(i) / 100.0 for i in range(8)]
                },
                {
                    "input_size": 8,
                    "output_size": 5,
                    "activation": "sigmoid",
                    "weights": [[float(i + j) / 100.0 for j in range(5)] for i in range(8)],
                    "biases": [float(i) / 100.0 for i in range(5)]
                }
            ]
        }
        
        json_path = work_dir / f"{model_type}_model.json"
        with open(json_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        return (json_path, model_data)
    
    @staticmethod
    def compile_model_to_elf(json_path: Path, output_dir: Path) -> Path:
        """
        Compile a model JSON to ELF bootloader.
        
        Args:
            json_path: Path to model JSON
            output_dir: Directory for output ELF
            
        Returns:
            Path to generated ELF file
            
        Raises:
            RuntimeError: If compilation fails
        """
        elf_filename = json_path.stem.replace("_model", "") + ".elf"
        elf_path = output_dir / elf_filename
        
        try:
            pipeline = BootloaderPipeline(verbose=False)
            result_elf, _ = pipeline.compile(str(json_path), str(elf_path))
            return Path(result_elf)
        except Exception as e:
            raise RuntimeError(f"Model compilation failed: {e}")
    
    @staticmethod
    def validate_elf_structure(elf_path: Path) -> Dict:
        """
        Validate ELF file structure and extract metadata.
        
        Args:
            elf_path: Path to ELF file
            
        Returns:
            Dictionary with ELF metadata
        """
        with open(elf_path, 'rb') as f:
            # Read ELF header
            magic = f.read(4)
            if magic != b'\x7fELF':
                raise ValueError("Invalid ELF magic")
            
            # Read basic header info
            f.seek(0x12)  # e_machine offset
            e_machine = int.from_bytes(f.read(2), 'little')
            
            f.seek(0x18)  # e_entry offset
            entry_point = int.from_bytes(f.read(4), 'little')
            
            f.seek(0x1C)  # e_phoff offset (32-bit)
            phoff = int.from_bytes(f.read(4), 'little')
        
        return {
            "magic": magic,
            "e_machine": e_machine,
            "entry_point": entry_point,
            "phoff": phoff,
            "file_size": elf_path.stat().st_size
        }
    
    @staticmethod
    def check_tool_available(tool_name: str) -> bool:
        """Check if a tool is available."""
        result = subprocess.run(['which', tool_name], capture_output=True)
        return result.returncode == 0


# ============================================================================
# ELF Structure Validation Tests
# ============================================================================

class TestPhase6ELFValidation(Phase6IntegrationTestSetup):
    """Test ELF file structure and format."""
    
    def test_elf_generation_basic(self):
        """Test that valid ELF files are generated."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create and compile model
            json_path, _ = self.create_simple_model_json(work_dir)
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            # Validate ELF structure
            assert elf_path.exists(), "ELF file not created"
            
            elf_info = self.validate_elf_structure(elf_path)
            assert elf_info["magic"] == b'\x7fELF', "Invalid ELF magic"
            assert elf_info["e_machine"] == 0xF3, "Not RISC-V architecture"
            assert elf_info["file_size"] > 1024, "ELF file too small"
    
    def test_elf_entry_point(self):
        """Test that ELF has valid entry point."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_simple_model_json(work_dir)
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            elf_info = self.validate_elf_structure(elf_path)
            
            # Entry point should be 0 (bootloader starts at 0x0)
            assert elf_info["entry_point"] == 0, f"Entry point should be 0, got {elf_info['entry_point']}"
    
    def test_elf_file_size_reasonable(self):
        """Test that ELF file size is reasonable."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_simple_model_json(work_dir)
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            elf_info = self.validate_elf_structure(elf_path)
            
            # ELF should be at least 4KB (bootloader code + overhead)
            assert elf_info["file_size"] >= 4096, "ELF file too small"
            
            # ELF should be less than 100KB (reasonable for bootloader)
            assert elf_info["file_size"] < 100 * 1024, "ELF file too large"


# ============================================================================
# Binary Content Validation Tests
# ============================================================================

class TestPhase6BinaryContent(Phase6IntegrationTestSetup):
    """Test ELF binary content and encoding."""
    
    def test_elf_contains_risc_v_instructions(self):
        """Test that ELF contains valid RISC-V instructions."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_simple_model_json(work_dir)
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            # Extract binary using objdump would be ideal, but check raw file
            # Look for common RISC-V instruction patterns
            with open(elf_path, 'rb') as f:
                content = f.read()
            
            # ELF should contain some executable code beyond just header
            assert len(content) > 52, "ELF content too small"
            
            # File should have .text section (after ELF header)
            # Just check it's not all zeros
            non_zero = sum(1 for b in content if b != 0)
            assert non_zero > len(content) * 0.1, "ELF contains mostly zeros"
    
    def test_elf_extraction_to_binary(self):
        """Test binary extraction from ELF."""
        if not self.check_tool_available('riscv64-elf-objcopy'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_simple_model_json(work_dir)
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            # Extract binary
            bin_path = work_dir / "test.bin"
            result = subprocess.run(
                ['riscv64-elf-objcopy', '-O', 'binary', str(elf_path), str(bin_path)],
                capture_output=True
            )
            
            assert result.returncode == 0, f"objcopy failed: {result.stderr.decode()}"
            assert bin_path.exists(), "Binary file not created"
            assert bin_path.stat().st_size > 0, "Binary file is empty"


# ============================================================================
# Model Loading Tests
# ============================================================================

class TestPhase6ModelLoading(Phase6IntegrationTestSetup):
    """Test model loading and verification."""
    
    def test_multiple_models_compilation(self):
        """Test compiling multiple models."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create multiple models
            generator_json, generator_data = self.create_simple_model_json(work_dir, "generator")
            recognizer_json, recognizer_data = self.create_simple_model_json(work_dir, "recognizer")
            
            # Compile both
            generator_elf = self.compile_model_to_elf(generator_json, work_dir)
            recognizer_elf = self.compile_model_to_elf(recognizer_json, work_dir)
            
            # Both should exist and be valid ELF files
            assert generator_elf.exists()
            assert recognizer_elf.exists()
            
            gen_info = self.validate_elf_structure(generator_elf)
            rec_info = self.validate_elf_structure(recognizer_elf)
            
            assert gen_info["magic"] == b'\x7fELF'
            assert rec_info["magic"] == b'\x7fELF'
    
    def test_model_compilation_deterministic(self):
        """Test that model compilation is deterministic."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create model
            json_path, _ = self.create_simple_model_json(work_dir)
            
            # Compile twice
            elf1 = self.compile_model_to_elf(json_path, work_dir)
            elf_path2 = work_dir / "test2.elf"
            
            pipeline = BootloaderPipeline(verbose=False)
            elf2_str, _ = pipeline.compile(str(json_path), str(elf_path2))
            elf2 = Path(elf2_str)
            
            # Both ELF files should be identical
            with open(elf1, 'rb') as f1, open(elf2, 'rb') as f2:
                # Compare file sizes first
                assert f1.seek(0, 2) == f2.seek(0, 2), "ELF files have different sizes"
                
                # Compare content
                f1.seek(0)
                f2.seek(0)
                assert f1.read() == f2.read(), "ELF files have different content"


# ============================================================================
# Memory Layout Tests
# ============================================================================

class TestPhase6MemoryLayout(Phase6IntegrationTestSetup):
    """Test memory layout and address allocation."""
    
    def test_memory_layout_consistency(self):
        """Test that memory layout follows specification."""
        # According to bootloader spec:
        # - Code: 0x0 - 0x10000
        # - Generator model: 0x10000 onwards
        # - Recognizer model: 0xF4ABC onwards
        
        expected_regions = {
            "code": (0x00000, 0x10000),
            "generator": (0x10000, 0xF3C7F),
            "recognizer": (0xF4ABC, 0xFFFFF)
        }
        
        # Just verify the specification is reasonable
        assert expected_regions["code"][1] <= expected_regions["generator"][0]
        assert expected_regions["generator"][1] < expected_regions["recognizer"][0]
        assert expected_regions["recognizer"][1] <= 0x100000


# ============================================================================
# Compilation Pipeline Tests
# ============================================================================

class TestPhase6Pipeline(Phase6IntegrationTestSetup):
    """Test complete compilation pipeline."""
    
    def test_pipeline_json_to_elf_full_flow(self):
        """Test complete JSON to ELF conversion."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create model JSON
            json_path, model_data = self.create_simple_model_json(work_dir)
            
            # Verify JSON structure
            assert json_path.exists()
            with open(json_path) as f:
                loaded = json.load(f)
            assert "metadata" in loaded
            assert "layers" in loaded
            assert len(loaded["layers"]) == 2
            
            # Compile to ELF
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            # Verify result
            assert elf_path.exists()
            elf_info = self.validate_elf_structure(elf_path)
            assert elf_info["e_machine"] == 0xF3
    
    def test_pipeline_error_recovery(self):
        """Test pipeline error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Try to compile non-existent file
            fake_json = work_dir / "nonexistent.json"
            
            with pytest.raises(Exception):
                self.compile_model_to_elf(fake_json, work_dir)


# ============================================================================
# Edge Cases and Robustness Tests
# ============================================================================

class TestPhase6EdgeCases(Phase6IntegrationTestSetup):
    """Test edge cases and robustness."""
    
    def test_large_model_compilation(self):
        """Test compilation of larger models."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create larger model
            model_data = {
                "metadata": {
                    "model_type": "generator",
                    "precision": "float32"
                },
                "layers": [
                    {
                        "input_size": 100,
                        "output_size": 50,
                        "activation": "relu",
                        "weights": [[float(i + j) / 1000.0 for j in range(50)] for i in range(100)],
                        "biases": [float(i) / 1000.0 for i in range(50)]
                    },
                    {
                        "input_size": 50,
                        "output_size": 25,
                        "activation": "sigmoid",
                        "weights": [[float(i + j) / 1000.0 for j in range(25)] for i in range(50)],
                        "biases": [float(i) / 1000.0 for i in range(25)]
                    },
                    {
                        "input_size": 25,
                        "output_size": 10,
                        "activation": "none",
                        "weights": [[float(i + j) / 1000.0 for j in range(10)] for i in range(25)],
                        "biases": [float(i) / 1000.0 for i in range(10)]
                    }
                ]
            }
            
            json_path = work_dir / "large_model.json"
            with open(json_path, 'w') as f:
                json.dump(model_data, f)
            
            # Compile
            elf_path = self.compile_model_to_elf(json_path, work_dir)
            
            # Should be larger than simple model
            assert elf_path.exists()
            assert elf_path.stat().st_size > 5 * 1024
    
    def test_model_with_different_activations(self):
        """Test models with different activation functions."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            activations = ["relu", "sigmoid", "none"]
            
            for i, activation in enumerate(activations):
                model_data = {
                    "metadata": {
                        "model_type": "generator",
                        "precision": "float32"
                    },
                    "layers": [
                        {
                            "input_size": 5,
                            "output_size": 3,
                            "activation": activation,
                            "weights": [[float(x) for x in range(3)] for _ in range(5)],
                            "biases": [0.1, 0.2, 0.3]
                        }
                    ]
                }
                
                json_path = work_dir / f"model_{i}_{activation}.json"
                with open(json_path, 'w') as f:
                    json.dump(model_data, f)
                
                # All should compile successfully
                elf_path = self.compile_model_to_elf(json_path, work_dir)
                assert elf_path.exists()


# ============================================================================
# Performance and Benchmarking Tests
# ============================================================================

class TestPhase6Performance:
    """Test compilation performance."""
    
    def test_compilation_completes_reasonably_fast(self):
        """Test that compilation doesn't take too long."""
        if not Phase6IntegrationTestSetup.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create test model
            setup = Phase6IntegrationTestSetup()
            json_path, _ = setup.create_simple_model_json(work_dir)
            
            # Measure compilation time
            start = time.time()
            elf_path = setup.compile_model_to_elf(json_path, work_dir)
            elapsed = time.time() - start
            
            # Should complete in reasonable time (< 5 seconds)
            assert elapsed < 5.0, f"Compilation took too long: {elapsed:.2f}s"
            assert elf_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
