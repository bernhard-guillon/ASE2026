#!/usr/bin/env python3
"""
Phase 4: Full Pipeline Integration Script

Orchestrates the complete model compilation pipeline:
1. JSON intermediate format → Model Compiler (Phase 1-2)
2. RISC-V assembly → Assembler (riscv64-elf-as)
3. Object file → Linker (riscv64-elf-ld with bootloader.ld)
4. ELF → Optional binary extraction (riscv64-elf-objcopy)

Single command replaces manual 4-step process.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from model_compiler import ModelCompiler


class BootloaderPipelineError(Exception):
    """Exception raised during pipeline execution."""
    pass


class BootloaderPipeline:
    """Orchestrates the complete model-to-bootloader compilation pipeline."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the pipeline.
        
        Args:
            verbose: Enable debug output
        """
        self.verbose = verbose
        self.work_dir = None
        self.json_path = None
        self.asm_path = None
        self.bin_path = None
        self.obj_path = None
        self.elf_path = None
        self.linker_script = None
    
    def find_linker_script(self) -> str:
        """
        Locate bootloader.ld linker script.
        
        Searches in current directory, then parent directories up to repo root.
        
        Returns:
            Path to bootloader.ld
            
        Raises:
            BootloaderPipelineError: If linker script not found
        """
        search_paths = [
            Path.cwd() / "bootloader.ld",
            Path.cwd().parent / "bootloader.ld",
            Path(__file__).parent / "bootloader.ld",
        ]
        
        for path in search_paths:
            if path.exists():
                if self.verbose:
                    print(f"[Pipeline] Found linker script: {path}")
                return str(path)
        
        raise BootloaderPipelineError(
            "Cannot find bootloader.ld. Expected in current directory or parent directory. "
            "Searched: " + ", ".join(str(p) for p in search_paths)
        )
    
    def find_tool(self, tool_name: str) -> str:
        """
        Find a RISC-V toolchain tool.
        
        Args:
            tool_name: Name of tool (e.g., 'riscv64-elf-as', 'riscv64-elf-ld')
            
        Returns:
            Full path to tool
            
        Raises:
            BootloaderPipelineError: If tool not found
        """
        tool_path = shutil.which(tool_name)
        if not tool_path:
            raise BootloaderPipelineError(
                f"Cannot find {tool_name}. Please install RISC-V GNU toolchain. "
                f"Expected command: {tool_name}"
            )
        if self.verbose:
            print(f"[Pipeline] Found {tool_name}: {tool_path}")
        return tool_path
    
    def stage_1_compile(self, json_path: str) -> Tuple[str, str]:
        """
        Stage 1: Compile JSON to RISC-V assembly using ModelCompiler.
        
        Args:
            json_path: Path to JSON intermediate format file
            
        Returns:
            Tuple of (asm_path, bin_path)
            
        Raises:
            BootloaderPipelineError: If compilation fails
        """
        if self.verbose:
            print("\n[Stage 1] Model Compilation (JSON → RISC-V Assembly)")
            print("=" * 60)
        
        try:
            # Use same directory as JSON for intermediate files
            json_abs = Path(json_path).resolve()
            work_dir = json_abs.parent
            
            asm_path = str(work_dir / json_abs.stem) + ".s"
            
            compiler = ModelCompiler(verbose=self.verbose)
            asm_file, bin_file = compiler.compile(str(json_abs), asm_path, with_bootloader=True)
            
            if self.verbose:
                asm_size = Path(asm_file).stat().st_size
                bin_size = Path(bin_file).stat().st_size
                print(f"✓ Assembly: {asm_file} ({asm_size} bytes)")
                print(f"✓ Binary:   {bin_file} ({bin_size} bytes)")
            
            return (asm_file, bin_file)
        
        except Exception as e:
            raise BootloaderPipelineError(f"Stage 1 (Compilation) failed: {e}")
    
    def stage_2_assemble(self, asm_path: str, obj_path: str) -> str:
        """
        Stage 2: Assemble RISC-V assembly to object file.
        
        Args:
            asm_path: Path to .s assembly file
            obj_path: Path to output .o object file
            
        Returns:
            Path to generated object file
            
        Raises:
            BootloaderPipelineError: If assembly fails
        """
        if self.verbose:
            print("\n[Stage 2] Assembly (RISC-V Assembly → Object File)")
            print("=" * 60)
        
        try:
            assembler = self.find_tool("riscv64-elf-as")
            
            cmd = [assembler, str(asm_path), "-o", str(obj_path)]
            if self.verbose:
                print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise BootloaderPipelineError(
                    f"Assembler failed:\n{result.stderr}"
                )
            
            if self.verbose:
                obj_size = Path(obj_path).stat().st_size
                print(f"✓ Object file: {obj_path} ({obj_size} bytes)")
            
            return str(obj_path)
        
        except BootloaderPipelineError:
            raise
        except Exception as e:
            raise BootloaderPipelineError(f"Stage 2 (Assembly) failed: {e}")
    
    def stage_3_link(self, obj_path: str, elf_path: str) -> str:
        """
        Stage 3: Link object file with linker script to generate ELF.
        
        Args:
            obj_path: Path to .o object file
            elf_path: Path to output .elf file
            
        Returns:
            Path to generated ELF file
            
        Raises:
            BootloaderPipelineError: If linking fails
        """
        if self.verbose:
            print("\n[Stage 3] Linking (Object → ELF Executable)")
            print("=" * 60)
        
        try:
            linker = self.find_tool("riscv64-elf-ld")
            linker_script = self.find_linker_script()
            
            cmd = [
                linker,
                "-T", linker_script,
                str(obj_path),
                "-o", str(elf_path)
            ]
            
            if self.verbose:
                print(f"Linker script: {linker_script}")
                print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise BootloaderPipelineError(
                    f"Linker failed:\n{result.stderr}"
                )
            
            if self.verbose:
                elf_size = Path(elf_path).stat().st_size
                print(f"✓ ELF file: {elf_path} ({elf_size} bytes)")
            
            return str(elf_path)
        
        except BootloaderPipelineError:
            raise
        except Exception as e:
            raise BootloaderPipelineError(f"Stage 3 (Linking) failed: {e}")
    
    def stage_4_extract_binary(self, elf_path: str, bin_path: str) -> str:
        """
        Stage 4 (Optional): Extract binary from ELF using objcopy.
        
        Args:
            elf_path: Path to .elf file
            bin_path: Path to output .bin file
            
        Returns:
            Path to generated binary file
            
        Raises:
            BootloaderPipelineError: If extraction fails
        """
        if self.verbose:
            print("\n[Stage 4] Binary Extraction (ELF → Raw Binary)")
            print("=" * 60)
        
        try:
            objcopy = self.find_tool("riscv64-elf-objcopy")
            
            cmd = [
                objcopy,
                "-O", "binary",
                str(elf_path),
                str(bin_path)
            ]
            
            if self.verbose:
                print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise BootloaderPipelineError(
                    f"Binary extraction failed:\n{result.stderr}"
                )
            
            if self.verbose:
                bin_size = Path(bin_path).stat().st_size
                print(f"✓ Binary: {bin_path} ({bin_size} bytes)")
            
            return str(bin_path)
        
        except BootloaderPipelineError:
            raise
        except Exception as e:
            raise BootloaderPipelineError(f"Stage 4 (Binary Extraction) failed: {e}")
    
    def compile(
        self,
        json_path: str,
        output_elf: str,
        output_bin: Optional[str] = None,
        skip_cleanup: bool = False
    ) -> Tuple[str, Optional[str]]:
        """
        Run complete pipeline: JSON → ELF (and optionally binary).
        
        Args:
            json_path: Input JSON intermediate format file
            output_elf: Output ELF file path
            output_bin: Optional output binary file path
            skip_cleanup: If True, keep intermediate .s and .o files
            
        Returns:
            Tuple of (elf_path, bin_path or None)
            
        Raises:
            BootloaderPipelineError: If any stage fails
        """
        self.json_path = str(Path(json_path).resolve())
        work_dir = Path(self.json_path).parent
        
        # Set up paths for intermediate files
        stem = Path(self.json_path).stem
        self.asm_path = str(work_dir / f"{stem}.bootloader.s")
        self.obj_path = str(work_dir / f"{stem}.bootloader.o")
        self.elf_path = str(Path(output_elf).resolve())
        self.bin_path = str(Path(output_bin).resolve()) if output_bin else None
        
        try:
            # Validate input
            if not Path(self.json_path).exists():
                raise BootloaderPipelineError(f"Input JSON file not found: {self.json_path}")
            
            if self.verbose:
                print(f"[Pipeline] Starting compilation pipeline")
                print(f"  Input:  {self.json_path}")
                print(f"  Output: {self.elf_path}")
                if self.bin_path:
                    print(f"  Binary: {self.bin_path}")
            
            # Stage 1: Compile JSON to assembly
            self.asm_path, _ = self.stage_1_compile(self.json_path)
            
            # Stage 2: Assemble to object file
            self.obj_path = self.stage_2_assemble(self.asm_path, self.obj_path)
            
            # Stage 3: Link to ELF
            self.elf_path = self.stage_3_link(self.obj_path, self.elf_path)
            
            # Stage 4: Extract binary if requested
            if self.bin_path:
                self.bin_path = self.stage_4_extract_binary(self.elf_path, self.bin_path)
            
            # Cleanup intermediate files unless requested otherwise
            if not skip_cleanup:
                for temp_file in [self.asm_path, self.obj_path]:
                    if Path(temp_file).exists():
                        if self.verbose:
                            print(f"[Cleanup] Removing {temp_file}")
                        Path(temp_file).unlink()
            
            if self.verbose:
                print("\n" + "=" * 60)
                print("[Pipeline] ✓ Compilation complete!")
                print("=" * 60)
            
            return (self.elf_path, self.bin_path)
        
        except BootloaderPipelineError:
            raise
        except Exception as e:
            raise BootloaderPipelineError(f"Pipeline failed: {e}")


def main():
    """CLI interface for compile_model_bootloader.py"""
    parser = argparse.ArgumentParser(
        description="Phase 4: Full bootloader compilation pipeline (JSON → ELF)"
    )
    parser.add_argument(
        "json_file",
        help="Path to JSON intermediate format file (model specification)"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output ELF file path (required)"
    )
    parser.add_argument(
        "--binary",
        default=None,
        help="Optional output binary file path (extracted from ELF)"
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Keep intermediate .s and .o files (default: cleaned up)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with progress information"
    )
    
    args = parser.parse_args()
    
    try:
        pipeline = BootloaderPipeline(verbose=args.verbose)
        elf_path, bin_path = pipeline.compile(
            args.json_file,
            args.output,
            output_bin=args.binary,
            skip_cleanup=args.skip_cleanup
        )
        
        print(f"✓ ELF bootloader: {elf_path}")
        if bin_path:
            print(f"✓ Binary bootloader: {bin_path}")
        
        return 0
    
    except BootloaderPipelineError as e:
        print(f"✗ Pipeline failed: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n✗ Pipeline interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
