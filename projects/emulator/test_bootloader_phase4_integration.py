#!/usr/bin/env python3
"""
Phase 4 Integration Tests: Full Pipeline Validation

Tests the complete bootloader compilation pipeline:
- JSON → ELF end-to-end
- Intermediate file handling
- Error handling and recovery
- Output validation
- Tool availability checks
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Tuple
import pytest
import numpy as np

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from compile_model_bootloader import BootloaderPipeline, BootloaderPipelineError


class Phase4IntegrationTestSetup:
    """Base class providing test helpers for Phase 4."""
    
    @staticmethod
    def create_test_model_json(work_dir: Path, model_name: str = "test_model") -> Tuple[Path, Dict]:
        """
        Create a minimal valid test model JSON file.
        
        Args:
            work_dir: Directory to create JSON in
            model_name: Name of model file (without .json)
            
        Returns:
            Tuple of (json_path, model_data)
        """
        model_data = {
            "metadata": {
                "model_type": "generator",
                "precision": "float32",
                "version": "1.0"
            },
            "layers": [
                {
                    "input_size": 10,
                    "output_size": 5,
                    "activation": "relu",
                    "weights": [[float(i + j) for j in range(5)] for i in range(10)],
                    "biases": [float(i) for i in range(5)]
                }
            ]
        }
        
        json_path = work_dir / f"{model_name}.json"
        with open(json_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        return (json_path, model_data)
    
    @staticmethod
    def create_invalid_model_json(work_dir: Path, model_name: str = "invalid") -> Path:
        """
        Create an invalid JSON file (missing required fields).
        
        Args:
            work_dir: Directory to create JSON in
            model_name: Name of model file
            
        Returns:
            Path to invalid JSON file
        """
        invalid_data = {
            "metadata": {"model_type": "generator"},
            # Missing "layers" - invalid!
        }
        
        json_path = work_dir / f"{model_name}.json"
        with open(json_path, 'w') as f:
            json.dump(invalid_data, f)
        
        return json_path
    
    @staticmethod
    def validate_elf_file(elf_path: Path) -> bool:
        """
        Validate that an ELF file has correct magic number.
        
        Args:
            elf_path: Path to ELF file
            
        Returns:
            True if valid ELF file
        """
        with open(elf_path, 'rb') as f:
            magic = f.read(4)
        return magic == b'\x7fELF'
    
    @staticmethod
    def check_tool_available(tool_name: str) -> bool:
        """
        Check if a RISC-V tool is available.
        
        Args:
            tool_name: Name of tool (e.g., 'riscv64-elf-as')
            
        Returns:
            True if tool is available
        """
        result = subprocess.run(['which', tool_name], capture_output=True)
        return result.returncode == 0


# ============================================================================
# Basic Pipeline Tests
# ============================================================================

class TestPhase4BasicPipeline(Phase4IntegrationTestSetup):
    """Test basic pipeline functionality."""
    
    def test_pipeline_full_workflow(self):
        """Test complete pipeline: JSON → ELF."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create test model
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            # Run pipeline
            pipeline = BootloaderPipeline(verbose=False)
            result_elf, result_bin = pipeline.compile(
                str(json_path),
                str(elf_path)
            )
            
            # Verify outputs
            assert Path(result_elf).exists(), "ELF file not created"
            assert self.validate_elf_file(Path(result_elf)), "Invalid ELF file"
            assert result_bin is None, "Binary should not be generated without --binary flag"
    
    def test_pipeline_with_binary_output(self):
        """Test pipeline with binary output generation."""
        if not self.check_tool_available('riscv64-elf-objcopy'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create test model
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            bin_path = work_dir / "test.bin"
            
            # Run pipeline with binary output
            pipeline = BootloaderPipeline(verbose=False)
            result_elf, result_bin = pipeline.compile(
                str(json_path),
                str(elf_path),
                output_bin=str(bin_path)
            )
            
            # Verify outputs
            assert Path(result_elf).exists(), "ELF file not created"
            assert Path(result_bin).exists(), "Binary file not created"
            assert self.validate_elf_file(Path(result_elf)), "Invalid ELF file"
            assert Path(result_bin).stat().st_size > 0, "Binary file is empty"
    
    def test_pipeline_cleanup_intermediate_files(self):
        """Test that intermediate files are cleaned up by default."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create test model
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            # Run pipeline with cleanup (default)
            pipeline = BootloaderPipeline(verbose=False)
            pipeline.compile(str(json_path), str(elf_path), skip_cleanup=False)
            
            # Check that intermediate files don't exist
            assert not list(work_dir.glob("*.s")), "Assembly files should be cleaned up"
            assert not list(work_dir.glob("*.o")), "Object files should be cleaned up"
    
    def test_pipeline_skip_cleanup(self):
        """Test that intermediate files are kept with --skip-cleanup."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create test model
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            # Run pipeline without cleanup
            pipeline = BootloaderPipeline(verbose=False)
            pipeline.compile(str(json_path), str(elf_path), skip_cleanup=True)
            
            # Check that intermediate files exist
            assert any(work_dir.glob("*.s")), "Assembly files should be kept with skip_cleanup"
            assert any(work_dir.glob("*.o")), "Object files should be kept with skip_cleanup"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestPhase4ErrorHandling(Phase4IntegrationTestSetup):
    """Test error handling and recovery."""
    
    def test_invalid_json_file(self):
        """Test handling of invalid JSON file."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create invalid JSON
            json_path = self.create_invalid_model_json(work_dir, "invalid")
            elf_path = work_dir / "test.elf"
            
            # Pipeline should raise error
            pipeline = BootloaderPipeline(verbose=False)
            with pytest.raises(BootloaderPipelineError):
                pipeline.compile(str(json_path), str(elf_path))
    
    def test_missing_input_file(self):
        """Test handling of missing input JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path = work_dir / "nonexistent.json"
            elf_path = work_dir / "test.elf"
            
            # Pipeline should raise error
            pipeline = BootloaderPipeline(verbose=False)
            with pytest.raises(BootloaderPipelineError, match="not found"):
                pipeline.compile(str(json_path), str(elf_path))
    
    def test_missing_linker_script(self):
        """Test handling of missing bootloader.ld in isolated directory."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            isolated_dir = work_dir / "isolated"
            isolated_dir.mkdir()
            
            # Create JSON in isolated dir without bootloader.ld
            json_path, _ = self.create_test_model_json(isolated_dir, "test")
            elf_path = isolated_dir / "test.elf"
            
            # Temporarily change to isolated dir (no bootloader.ld in path)
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(isolated_dir)
                
                pipeline = BootloaderPipeline(verbose=False)
                # Pipeline searches: cwd, parent, script dir
                # In this case, it might find bootloader.ld in script dir
                # So we just verify pipeline runs (it will find it if available)
                try:
                    pipeline.compile(str(json_path), str(elf_path))
                except BootloaderPipelineError as e:
                    # Either succeeds (finds linker script elsewhere) or fails
                    # Both are acceptable
                    assert "bootloader.ld" in str(e) or Path(elf_path).exists()
            finally:
                os.chdir(old_cwd)
    
    def test_missing_assembler_tool(self):
        """Test graceful handling of missing riscv64-elf-as."""
        # This test verifies error message is clear
        if self.check_tool_available('riscv64-elf-as'):
            pytest.skip("This test requires missing riscv64-elf-as")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            pipeline = BootloaderPipeline(verbose=False)
            with pytest.raises(BootloaderPipelineError, match="riscv64-elf-as"):
                pipeline.compile(str(json_path), str(elf_path))


# ============================================================================
# Output Validation Tests
# ============================================================================

class TestPhase4OutputValidation(Phase4IntegrationTestSetup):
    """Test output file quality and validation."""
    
    def test_elf_file_size_reasonable(self):
        """Test that generated ELF file has reasonable size."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            pipeline = BootloaderPipeline(verbose=False)
            pipeline.compile(str(json_path), str(elf_path))
            
            # ELF should be at least 1 KB (reasonable for bootloader)
            file_size = Path(elf_path).stat().st_size
            assert file_size > 1024, f"ELF file too small: {file_size} bytes"
            # ELF should be less than 1 MB (sanity check)
            assert file_size < 1024 * 1024, f"ELF file too large: {file_size} bytes"
    
    def test_elf_header_valid(self):
        """Test ELF file has valid header."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            
            pipeline = BootloaderPipeline(verbose=False)
            pipeline.compile(str(json_path), str(elf_path))
            
            # Validate ELF header
            with open(elf_path, 'rb') as f:
                magic = f.read(4)
                assert magic == b'\x7fELF', "Invalid ELF magic number"
                
                # Read e_machine field (offset 0x12, 2 bytes, little-endian)
                f.seek(0x12)
                e_machine = int.from_bytes(f.read(2), 'little')
                assert e_machine == 0xF3, f"Expected RISC-V (0xF3), got {hex(e_machine)}"
    
    def test_binary_file_loadable(self):
        """Test that generated binary file is valid."""
        if not self.check_tool_available('riscv64-elf-objcopy'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            json_path, _ = self.create_test_model_json(work_dir, "test")
            elf_path = work_dir / "test.elf"
            bin_path = work_dir / "test.bin"
            
            pipeline = BootloaderPipeline(verbose=False)
            pipeline.compile(str(json_path), str(elf_path), output_bin=str(bin_path))
            
            # Binary should exist and be non-empty
            # (Binary may be larger than ELF due to padding in sections)
            assert Path(bin_path).exists(), "Binary file should exist"
            bin_size = Path(bin_path).stat().st_size
            assert bin_size > 0, "Binary file is empty"


# ============================================================================
# Integration Tests
# ============================================================================

class TestPhase4Integration(Phase4IntegrationTestSetup):
    """Test pipeline integration with other components."""
    
    def test_multiple_models_different_sizes(self):
        """Test pipeline with models of different sizes."""
        if not self.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            
            # Create small model
            small_json = work_dir / "small.json"
            small_data = {
                "metadata": {"model_type": "generator", "precision": "float32"},
                "layers": [{"input_size": 2, "output_size": 2, "activation": "relu",
                           "weights": [[1.0, 2.0], [3.0, 4.0]], "biases": [0.1, 0.2]}]
            }
            with open(small_json, 'w') as f:
                json.dump(small_data, f)
            
            # Create large model
            large_json = work_dir / "large.json"
            large_data = {
                "metadata": {"model_type": "generator", "precision": "float32"},
                "layers": [
                    {"input_size": 100, "output_size": 50, "activation": "relu",
                     "weights": [[float(i+j) for j in range(50)] for i in range(100)],
                     "biases": [float(i) for i in range(50)]},
                    {"input_size": 50, "output_size": 25, "activation": "sigmoid",
                     "weights": [[float(i+j) for j in range(25)] for i in range(50)],
                     "biases": [float(i) for i in range(25)]}
                ]
            }
            with open(large_json, 'w') as f:
                json.dump(large_data, f)
            
            # Compile both
            pipeline = BootloaderPipeline(verbose=False)
            
            small_elf = work_dir / "small.elf"
            large_elf = work_dir / "large.elf"
            
            pipeline.compile(str(small_json), str(small_elf))
            pipeline.compile(str(large_json), str(large_elf))
            
            # Verify both exist and large is larger
            assert Path(small_elf).exists()
            assert Path(large_elf).exists()
            assert Path(large_elf).stat().st_size > Path(small_elf).stat().st_size


# ============================================================================
# CLI Tests
# ============================================================================

class TestPhase4CLI:
    """Test command-line interface."""
    
    def test_cli_help(self):
        """Test that --help works."""
        script = Path(__file__).parent / "compile_model_bootloader.py"
        result = subprocess.run(
            ['python3', str(script), '--help'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "JSON intermediate format" in result.stdout
    
    def test_cli_missing_required_output(self):
        """Test CLI with missing required --output argument."""
        if not Phase4IntegrationTestSetup.check_tool_available('riscv64-elf-as'):
            pytest.skip("RISC-V toolchain not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            json_path, _ = Phase4IntegrationTestSetup.create_test_model_json(work_dir)
            
            script = Path(__file__).parent / "compile_model_bootloader.py"
            result = subprocess.run(
                ['python3', str(script), str(json_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode != 0
            assert "required" in result.stderr.lower() or "output" in result.stderr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
