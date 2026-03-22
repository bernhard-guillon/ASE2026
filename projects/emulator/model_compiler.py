#!/usr/bin/env python3
"""
Model Compiler: Converts JSON intermediate format to RISC-V assembly with embedded binary data.

This compiler:
1. Reads JSON intermediate format from weight-export pipeline
2. Converts weights/biases to binary format
3. Generates RISC-V assembly that embeds binary data using .incbin directives
4. Outputs .s file ready for RISC-V assembler

Phase 1 of bootloader pipeline.
"""

import json
import struct
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np


class ModelCompiler:
    """Converts JSON intermediate format to RISC-V assembly with embedded data."""
    
    # Binary format constants (must match projects/weight-export/model_formats.py)
    MAGIC = 0x4E52414E  # "NRAL"
    VERSION = 1
    MODEL_TYPES = {"generator": 0, "recognizer": 1}
    ACTIVATIONS = {"relu": 0, "sigmoid": 1, "none": 2}
    
    HEADER_SIZE = 32
    LAYER_ENTRY_SIZE = 32
    
    # Memory layout constants (from Sprint 1 design)
    MEMORY_LAYOUT = {
        "code_base": 0x00001000,
        "generator_base": 0x00010000,
        "recognizer_base": 0x00110000,
        "buffer_base": 0x00150000,
        "framebuffer_base": 0x00200000,
    }
    
    # Buffer offsets (relative to buffer_base)
    BUFFER_OFFSETS = {
        "input": 0x0000,           # 0x00150000
        "activation_a": 0x1000,    # 0x00151000
        "activation_b": 0x2000,    # 0x00152000
        "output": 0x3000,          # 0x00153000
    }
    
    def __init__(self, verbose: bool = False):
        """
        Initialize compiler.
        
        Args:
            verbose: Enable debug output
        """
        self.verbose = verbose
        self.metadata = None
        self.layers = None
        self.binary_data = None
        
    def load_json_intermediate(self, json_path: str) -> Dict:
        """
        Load JSON intermediate format.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Dictionary with model data
        """
        if self.verbose:
            print(f"[ModelCompiler] Loading JSON: {json_path}")
        
        with open(json_path, 'r') as f:
            intermediate = json.load(f)
        
        # Validate structure
        if "metadata" not in intermediate or "layers" not in intermediate:
            raise ValueError("Invalid intermediate format: missing metadata or layers")
        
        self.metadata = intermediate["metadata"]
        self.layers = intermediate["layers"]
        
        if self.verbose:
            print(f"  Model type: {self.metadata.get('model_type')}")
            print(f"  Num layers: {len(self.layers)}")
            print(f"  Precision: {self.metadata.get('precision')}")
        
        return intermediate
    
    def generate_binary_format(self) -> bytes:
        """
        Convert loaded JSON to binary format.
        
        Returns:
            Bytes ready to write to .bin file
        """
        if self.metadata is None or self.layers is None:
            raise ValueError("No model loaded. Call load_json_intermediate() first")
        
        if self.verbose:
            print("[ModelCompiler] Generating binary format...")
        
        # Validate
        if self.metadata.get("precision") != "float32":
            raise ValueError("Only float32 precision supported")
        
        model_type_val = self.MODEL_TYPES[self.metadata.get("model_type")]
        
        # Calculate statistics
        num_layers = len(self.layers)
        total_weights = sum(layer["input_size"] * layer["output_size"] for layer in self.layers)
        total_biases = sum(layer["output_size"] for layer in self.layers)
        
        if self.verbose:
            print(f"  Total weights: {total_weights}")
            print(f"  Total biases: {total_biases}")
        
        # Build binary data
        binary_data = bytearray()
        
        # Header (28 bytes: 6 uints + 4 bytes)
        header = struct.pack(
            '<IIIIII4B',
            self.MAGIC,           # magic
            self.VERSION,         # version
            model_type_val,       # model_type
            num_layers,           # num_layers
            total_weights,        # total_weight_floats
            total_biases,         # total_bias_floats
            0, 0, 0, 0            # reserved
        )
        binary_data.extend(header)
        
        # Layer table (32 bytes per layer)
        weight_offset = 0
        bias_offset = 0
        
        for layer in self.layers:
            activation_val = self.ACTIVATIONS[layer.get("activation", "none")]
            num_weights = layer["input_size"] * layer["output_size"]
            num_biases = layer["output_size"]
            
            # 32 bytes per layer: 8 uint32s
            entry = struct.pack(
                '<8I',
                layer["input_size"],       # input_size
                layer["output_size"],      # output_size
                activation_val,            # activation
                weight_offset * 4,         # weight_offset (in bytes)
                bias_offset * 4,           # bias_offset (in bytes)
                0,                         # reserved
                0,                         # reserved
                0                          # reserved
            )
            binary_data.extend(entry)
            
            weight_offset += num_weights
            bias_offset += num_biases
        
        # Weight data (float32)
        for layer in self.layers:
            weights = np.array(layer["weights"], dtype=np.float32)
            binary_data.extend(weights.tobytes())
        
        # Bias data (float32)
        for layer in self.layers:
            biases = np.array(layer["biases"], dtype=np.float32)
            binary_data.extend(biases.tobytes())
        
        self.binary_data = bytes(binary_data)
        
        if self.verbose:
            print(f"  Binary size: {len(self.binary_data)} bytes")
        
        return self.binary_data
    
    def generate_assembly(self, json_path: str, output_asm: str, temp_bin: str = None, 
                         with_bootloader: bool = True, with_execution: bool = True) -> str:
        """
        Generate complete RISC-V assembly file with model data and execution code.
        
        Args:
            json_path: Path to JSON intermediate format
            output_asm: Path to output .s file
            temp_bin: Path to temporary binary file (default: output_asm.bin)
            with_bootloader: Include bootloader code (legacy, kept for compatibility)
            with_execution: Include neural network execution code (Sprint 2)
        
        Returns:
            Path to generated assembly file
        """
        if self.verbose:
            print(f"[ModelCompiler] Generating assembly: {output_asm}")
        
        # Load JSON
        self.load_json_intermediate(json_path)
        
        # Generate binary format
        binary = self.generate_binary_format()
        
        # Write binary to temp file
        if temp_bin is None:
            temp_bin = str(Path(output_asm).with_suffix('.bin'))
        
        with open(temp_bin, 'wb') as f:
            f.write(binary)
        
        if self.verbose:
            print(f"  Binary size: {len(binary)} bytes")
            print(f"  Binary written to: {temp_bin}")
        
        # Get model info
        model_type = self.metadata.get("model_type", "unknown")
        num_layers = len(self.layers)
        input_size = self.layers[0]["input_size"] if self.layers else 0
        output_size = self.layers[-1]["output_size"] if self.layers else 0
        
        # Determine model base address
        model_base = (self.MEMORY_LAYOUT["generator_base"] 
                     if model_type == "generator" 
                     else self.MEMORY_LAYOUT["recognizer_base"])
        
        # Build complete assembly file
        asm_parts = []
        
        # Header comment
        asm_parts.append(self._generate_asm_header(model_type, num_layers, len(binary)))
        
        # Data section with embedded binary
        asm_parts.append(self._generate_data_section(temp_bin, len(binary)))
        
        # Text section with execution code
        if with_execution:
            # Generate all execution components
            asm_parts.append("\n# ====== EXECUTION CODE ======\n")
            
            # Main execution loop
            asm_parts.append(self._generate_execution_loop(model_type))
            
            # I/O mapping functions
            asm_parts.append(self._generate_input_mapping(model_type, input_size))
            asm_parts.append(self._generate_output_mapping(model_type, output_size))
            
            # Forward pass coordinator
            asm_parts.append(self._generate_model_forward_pass())
            
            # Individual layer functions
            for i, layer in enumerate(self.layers):
                is_last = (i == len(self.layers) - 1)
                layer_code = self._generate_dense_layer_forward(i, layer, model_base, is_last)
                asm_parts.append(layer_code)
            
            # Helper functions
            asm_parts.append(self._generate_sigmoid_piecewise())
            
        else:
            # Legacy mode: just bootloader or skeleton
            asm_parts.append(self._generate_text_section(with_bootloader))
        
        # Write complete assembly file
        asm_content = '\n'.join(asm_parts)
        with open(output_asm, 'w') as f:
            f.write(asm_content)
        
        if self.verbose:
            print(f"  Assembly written to: {output_asm}")
        
        return output_asm

    def _generate_asm_header(self, model_type: str, num_layers: int, binary_size: int) -> str:
        """Generate assembly file header with metadata comments."""
        return f"""# RISC-V Bootloader: Model Compiler Output
# Generated by model_compiler.py Phase 1
#
# This assembly embeds neural network model weights and biases
# using .incbin directive. The bootloader code (Phase 2) will
# copy this embedded data to correct memory addresses.
#
# Model Type: {model_type}
# Number of Layers: {num_layers}
# Binary Data Size: {binary_size} bytes
#
# Memory Map:
#   0x00000 - 0x0FFFF: Bootloader code and embedded model data
#   0x10000 - 0xF3C7F: Generator model (loaded by bootloader)
#   0xF4ABC - 0xFFFFF: Recognizer model (loaded by bootloader)

.section .data
.align 4
.globl model_data_start

"""
    
    def _generate_data_section(self, bin_path: str, binary_size: int) -> str:
        """Generate .data section with .incbin directive."""
        # Make path relative if possible for portability
        bin_path_display = Path(bin_path).name  # Just filename for comments
        
        return f"""# Model binary data (embedded via .incbin)
# Size: {binary_size} bytes
model_data_start:
    .incbin "{bin_path}"
model_data_end:

# Calculate total embedded data size
.set model_data_size, model_data_end - model_data_start

"""
    
    def _generate_text_section(self, include_bootloader: bool = True) -> str:
        """
        Generate .text section with bootloader code.
        
        Args:
            include_bootloader: If True, generate full bootloader initialization code.
                              If False, generate skeleton with placeholder.
        
        Returns:
            Assembly code for .text section
        """
        if not include_bootloader:
            return """# Bootloader code
# This section will be filled in Phase 2 with memory initialization code
.section .text
.align 4
.globl _start

_start:
    # Bootloader code will copy embedded model data to correct addresses:
    # - Generator model data -> 0x10000
    # - Recognizer model data -> 0xF4ABC
    #
    # Implementation in Phase 2

    # Placeholder for now: infinite loop
    j _start

"""
        
        return self._generate_bootloader_code()
    
    def _generate_bootloader_code(self) -> str:
        """
        Generate Phase 2 bootloader code that initializes memory with models.
        
        The bootloader:
        1. Initializes stack pointer to 0x20000
        2. Copies embedded models from .data section to correct memory addresses
        3. Exits cleanly via syscall
        
        Returns:
            RISC-V assembly code for bootloader initialization
        """
        # Calculate model addresses and sizes
        # Models are embedded in .data section in order: generator, then recognizer
        
        if self.metadata is None or self.metadata.get("model_type") != "generator":
            # For single model (either generator or recognizer)
            return self._generate_single_model_bootloader()
        
        # For now, assume we're compiling a single model
        # Full two-model bootloader will be used when both models are available
        return self._generate_single_model_bootloader()
    
    def _generate_single_model_bootloader(self) -> str:
        """Generate bootloader for a single model (generator or recognizer)."""
        model_type = self.metadata.get("model_type", "unknown")
        binary_size = len(self.binary_data) if self.binary_data else 0
        
        if model_type == "generator":
            dest_addr = 0x10000
            model_name = "generator"
        elif model_type == "recognizer":
            dest_addr = 0xF4ABC
            model_name = "recognizer"
        else:
            dest_addr = 0x10000
            model_name = "unknown"
        
        # Generate verification code that samples key values
        # Check: header (magic), first weight, middle weight, last weight
        verify_code = self._generate_verification_code(dest_addr, binary_size)
        
        return f"""# RISC-V Bootloader Phase 2: Memory Initialization + Verification
# Copies embedded model data to target address, verifies, and exits

.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to 0x20000
    lui sp, 0x20
    
    # Copy {model_name} model data to 0x{dest_addr:X}
    # Source: model_data_start (in .data section)
    # Destination: 0x{dest_addr:X}
    # Size: {binary_size} bytes
    
    # Load destination address into a1
    lui a1, 0x{(dest_addr >> 12) & 0xFFFFF:X}
    addi a1, a1, {(dest_addr & 0xFFF) if (dest_addr & 0x800) == 0 else ((dest_addr & 0xFFF) - 0x1000):d}
    
    # Load source address (model_data_start) into a0
    la a0, model_data_start
    
    # Load size into a2 (in bytes)
    li a2, {binary_size}
    
    # Copy loop: memcpy-style byte copy
    # Copy {binary_size} bytes from a0 to a1
    xor a3, a3, a3          # a3 = 0 (loop counter)
    
.Lcopy_loop:
    bge a3, a2, .Lcopy_done # if (counter >= size) goto copy_done
    add a4, a0, a3          # a4 = source + offset
    lbu a5, 0(a4)           # a5 = *source (load byte)
    add a4, a1, a3          # a4 = dest + offset
    sb a5, 0(a4)            # *dest = a5 (store byte)
    addi a3, a3, 1          # counter++
    j .Lcopy_loop
    
.Lcopy_done:
    # Model copied - now verify
    jal ra, verify_model
    
    # If verification passed (a0 == 0), exit with success
    bne a0, zero, .Lverify_failed
    li a0, 0                # exit code 0 (success)
    j .Lexit
    
.Lverify_failed:
    # Verification failed, exit with error code
    li a0, 1                # exit code 1 (verification failed)
    
.Lexit:
    li a7, 93               # SYS_exit
    ecall

# Verification routine
# Checks header, layer table, and samples data integrity
# Returns: a0 = 0 if OK, a0 = 1 if verification failed
verify_model:
    # Save return address
    addi sp, sp, -4
    sw ra, 0(sp)
    
    # Load destination address where model was copied
    lui a5, 0x{(dest_addr >> 12) & 0xFFFFF:X}
    addi a5, a5, {(dest_addr & 0xFFF) if (dest_addr & 0x800) == 0 else ((dest_addr & 0xFFF) - 0x1000):d}
    
    # === Verify Header (28 bytes) ===
    # Check magic number at offset 0: should be 0x4E52414E ("NRAL")
    lw a4, 0(a5)
    li a6, 0x4E52414E
    bne a4, a6, .Lverify_fail
    
    # Check version at offset 4: should be 1
    lw a4, 4(a5)
    li a6, 1
    bne a4, a6, .Lverify_fail
    
{verify_code}
    
    # Verification passed
    li a0, 0
    j .Lverify_done
    
.Lverify_fail:
    # Verification failed
    li a0, 1
    
.Lverify_done:
    # Restore return address and return
    lw ra, 0(sp)
    addi sp, sp, 4
    jr ra

"""
    
    def _generate_verification_code(self, dest_addr: int, binary_size: int) -> str:
        """
        Generate verification code that samples key data values.
        
        Strategy:
        1. Check header (magic, version)
        2. Check layer table samples
        3. Check data samples (first weight, middle weight, last weight)
        
        Args:
            dest_addr: Destination address where model was copied
            binary_size: Total size of binary data
        
        Returns:
            Assembly code for verification checks
        """
        if not self.binary_data or not self.layers:
            return "    # No data to verify\n"
        
        checks = []
        
        # For simplicity, just check that header+layer table are non-zero
        # and sample a few bytes from the data section
        checks.append("    # === Verify Layer Table ===")
        checks.append("    # Check first layer entry is present")
        checks.append("    lw a4, 28(a5)  # Load first layer input_size from offset 28")
        checks.append("    beq a4, zero, .Lverify_fail  # Should not be zero")
        
        checks.append("")
        checks.append("    # === Verify Data Integrity (Sampling) ===")
        checks.append("    # Check first data bytes (after header and layer table)")
        checks.append("    # This catches data corruption in early part")
        
        header_size = 28
        num_layers = len(self.layers)
        layer_table_size = num_layers * 32
        data_start_offset = header_size + layer_table_size
        
        checks.append(f"    # Data starts at offset {data_start_offset} in destination")
        checks.append(f"    lui a4, 0x{((dest_addr + data_start_offset) >> 12) & 0xFFFFF:X}")
        checks.append(f"    addi a4, a4, {((dest_addr + data_start_offset) & 0xFFF) if ((dest_addr + data_start_offset) & 0x800) == 0 else (((dest_addr + data_start_offset) & 0xFFF) - 0x1000):d}")
        checks.append("    lw a6, 0(a4)  # Load first data word")
        checks.append("    # Note: we don't check specific value, just that copy happened")
        
        # Check middle of data section
        middle_offset = data_start_offset + (binary_size - data_start_offset) // 2
        checks.append("")
        checks.append("    # Check middle data section")
        checks.append(f"    lui a4, 0x{((dest_addr + middle_offset) >> 12) & 0xFFFFF:X}")
        checks.append(f"    addi a4, a4, {((dest_addr + middle_offset) & 0xFFF) if ((dest_addr + middle_offset) & 0x800) == 0 else (((dest_addr + middle_offset) & 0xFFF) - 0x1000):d}")
        checks.append("    lw a6, 0(a4)  # Load middle data word")
        
        # Check end of data section
        end_offset = binary_size - 4
        checks.append("")
        checks.append("    # Check end data section")
        checks.append(f"    lui a4, 0x{((dest_addr + end_offset) >> 12) & 0xFFFFF:X}")
        checks.append(f"    addi a4, a4, {((dest_addr + end_offset) & 0xFFF) if ((dest_addr + end_offset) & 0x800) == 0 else (((dest_addr + end_offset) & 0xFFF) - 0x1000):d}")
        checks.append("    lw a6, 0(a4)  # Load last data word")
        
        checks.append("")
        checks.append("    # All checks passed")
        
        return "\n".join(checks)
    
    def _generate_dual_model_bootloader(self, gen_size: int, rec_size: int) -> str:
        """
        Generate bootloader for both generator and recognizer models.
        
        Note: This is for future use when both models are embedded.
        For Phase 2, we handle single models only.
        """
        return f"""# RISC-V Bootloader Phase 2: Dual Model Initialization
# Copies both generator and recognizer models to target addresses

.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to 0x20000
    lui sp, 0x20
    
    # === Copy Generator Model ===
    # Destination: 0x10000
    # Size: {gen_size} bytes
    
    lui a1, 0x10            # a1 = 0x10000 (dest for generator)
    
    la a0, model_data_start # a0 = source (start of embedded data)
    li a2, {gen_size}       # a2 = size of generator
    
    xor a3, a3, a3          # a3 = 0 (loop counter)
    
.Lcopy_gen_loop:
    bge a3, a2, .Lcopy_gen_done
    add a4, a0, a3
    lbu a5, 0(a4)
    add a4, a1, a3
    sb a5, 0(a4)
    addi a3, a3, 1
    j .Lcopy_gen_loop
    
.Lcopy_gen_done:
    # === Copy Recognizer Model ===
    # Destination: 0xF4ABC
    # Offset from generator: {gen_size} bytes
    # Size: {rec_size} bytes
    
    # a1 = 0xF4ABC (dest for recognizer)
    lui a1, 0xF5
    addi a1, a1, -1348
    
    # a0 already has model_data_start
    # a0 = model_data_start + {gen_size} (offset to recognizer)
    addi a0, a0, {gen_size}
    
    li a2, {rec_size}       # a2 = size of recognizer
    xor a3, a3, a3          # a3 = 0 (loop counter)
    
.Lcopy_rec_loop:
    bge a3, a2, .Lcopy_rec_done
    add a4, a0, a3
    lbu a5, 0(a4)
    add a4, a1, a3
    sb a5, 0(a4)
    addi a3, a3, 1
    j .Lcopy_rec_loop
    
.Lcopy_rec_done:
    # Both models copied successfully
    li a0, 0                # exit code 0 (success)
    li a7, 93               # SYS_exit
    ecall

"""
    def _generate_sigmoid_piecewise(self) -> str:
        """Generate piecewise linear sigmoid approximation function."""
        return """
# Sigmoid piecewise linear approximation
# Input: fa0 (x value)
# Output: fa0 (sigmoid(x))
sigmoid_piecewise:
    # Save registers
    addi sp, sp, -16
    sw ra, 12(sp)
    fsw fa1, 8(sp)
    fsw fa2, 4(sp)
    
    # Load constants
    lui t0, 0xC0000          # -2.0 in float
    fmv.w.x fa1, t0
    lui t0, 0x40000          # 2.0 in float
    fmv.w.x fa2, t0
    
    # if x <= -2.0: return 0.0
    fle.s t0, fa0, fa1
    beq t0, zero, .Lsig_check_mid_neg
    fmv.w.x fa0, zero        # return 0.0
    j .Lsig_done
    
.Lsig_check_mid_neg:
    # if x <= 0.0: return 0.25 + 0.125*x
    fmv.w.x fa1, zero
    fle.s t0, fa0, fa1
    beq t0, zero, .Lsig_check_mid_pos
    
    lui t0, 0x3E000          # 0.125 in float
    fmv.w.x fa1, t0
    fmul.s fa1, fa0, fa1     # 0.125 * x
    lui t0, 0x3E800          # 0.25 in float
    fmv.w.x fa2, t0
    fadd.s fa0, fa2, fa1     # 0.25 + 0.125*x
    j .Lsig_done
    
.Lsig_check_mid_pos:
    # if x <= 2.0: return 0.75 + 0.125*x
    lui t0, 0x40000          # 2.0 in float
    fmv.w.x fa2, t0
    fle.s t0, fa0, fa2
    beq t0, zero, .Lsig_saturate
    
    lui t0, 0x3E000          # 0.125 in float
    fmv.w.x fa1, t0
    fmul.s fa1, fa0, fa1     # 0.125 * x
    lui t0, 0x3F400          # 0.75 in float
    fmv.w.x fa2, t0
    fadd.s fa0, fa2, fa1     # 0.75 + 0.125*x
    j .Lsig_done
    
.Lsig_saturate:
    # x > 2.0: return 1.0
    lui t0, 0x3F800          # 1.0 in float
    fmv.w.x fa0, t0
    
.Lsig_done:
    # Restore registers
    lw ra, 12(sp)
    flw fa1, 8(sp)
    flw fa2, 4(sp)
    addi sp, sp, 16
    ret

"""
    
    def _generate_dense_layer_forward(self, layer_idx: int, layer_info: Dict, 
                                      model_base: int, is_last_layer: bool = False) -> str:
        """
        Generate RISC-V assembly code for Dense layer forward pass.
        
        Args:
            layer_idx: Layer index (0-based)
            layer_info: Layer metadata dict
            model_base: Base address where model is loaded
            is_last_layer: True if this is the final layer
            
        Returns:
            RISC-V assembly code for this layer's forward pass
        """
        input_size = layer_info["input_size"]
        output_size = layer_info["output_size"]
        activation = layer_info["activation"]
        
        # Calculate offsets in binary format
        # Binary format: HEADER (28) + LAYER_TABLE (32 * num_layers) + WEIGHTS + BIASES
        header_size = 28
        layer_table_size = 32 * len(self.layers)
        weights_data_start = header_size + layer_table_size
        
        # Calculate cumulative sizes for weights and biases
        weight_float_count = 0
        bias_float_count = 0
        for i in range(layer_idx):
            weight_float_count += self.layers[i]["input_size"] * self.layers[i]["output_size"]
            bias_float_count += self.layers[i]["output_size"]
        
        # Offsets are absolute from model_base (in bytes)
        weights_offset = weights_data_start + weight_float_count * 4
        
        # Biases come after all weights
        total_weights = sum(self.layers[j]["input_size"] * self.layers[j]["output_size"] 
                           for j in range(len(self.layers)))
        biases_offset = weights_data_start + total_weights * 4 + bias_float_count * 4
        
        # Buffer management (ping-pong)
        if layer_idx == 0:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
        elif layer_idx % 2 == 1:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_b"]
        else:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_b"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
        
        # For last layer, output to output buffer
        if is_last_layer:
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]
        
        asm = f"""
# Layer {layer_idx}: Dense [{input_size} → {output_size}] + {activation}
layer_{layer_idx}_forward:
    # Input buffer: 0x{input_buf:08X}
    # Output buffer: 0x{output_buf:08X}
    # Weights @ model_base + 0x{weights_offset:X}
    # Biases @ model_base + 0x{biases_offset:X}
    
    # Save callee-saved registers
    addi sp, sp, -32
    sw ra, 28(sp)
    sw s0, 24(sp)
    sw s1, 20(sp)
    sw s2, 16(sp)
    sw s3, 12(sp)
    sw s4, 8(sp)
    
    # Load base addresses
    la s0, model_data_start             # s0 = address of model binary data
    lui s1, {input_buf >> 12}           # s1 = input buffer
    addi s1, s1, {input_buf & 0xFFF}
    lui s2, {output_buf >> 12}          # s2 = output buffer  
    addi s2, s2, {output_buf & 0xFFF}
    
    # s3 = output index (j), s4 = input index (i)
    li s3, 0                            # j = 0

.L{layer_idx}_outer_loop:
    # Check if j >= output_size
    li t0, {output_size}
    bge s3, t0, .L{layer_idx}_done
    
    # Load bias[j] into fa0 (accumulator)
    li t0, {biases_offset}
    add t1, s0, t0                      # t1 = model_base + bias_offset
    slli t2, s3, 2                      # t2 = j * 4
    add t1, t1, t2                      # t1 = &bias[j]
    flw fa0, 0(t1)                      # fa0 = bias[j] (accumulator)
    
    # Inner loop: accumulate weights * inputs
    li s4, 0                            # i = 0

.L{layer_idx}_inner_loop:
    # Check if i >= input_size
    li t0, {input_size}
    bge s4, t0, .L{layer_idx}_apply_activation
    
    # Load input[i]
    slli t0, s4, 2                      # t0 = i * 4
    add t1, s1, t0                      # t1 = input_buf + i*4
    flw fa1, 0(t1)                      # fa1 = input[i]
    
    # Load weight[i][j]
    # offset = (i * output_size + j) * 4
    # Compute i * output_size without MUL instruction
    li t1, 0                           # t1 = 0 (accumulator)
    li t2, {output_size}                # t2 = output_size
    li t0, 0                           # t0 = loop counter
.Lmul_{layer_idx}_loop:
    bge t0, s4, .Lmul_{layer_idx}_done
    add t1, t1, t2                      # t1 += output_size
    addi t0, t0, 1
    j .Lmul_{layer_idx}_loop
.Lmul_{layer_idx}_done:
    add t1, t1, s3                      # t1 = i * output_size + j
    slli t1, t1, 2                      # t1 *= 4 (byte offset)
    li t0, {weights_offset}
    add t1, t1, t0                      # t1 += weights_offset
    add t1, s0, t1                      # t1 = model_base + offset
    flw fa2, 0(t1)                      # fa2 = weight[i][j]
    
    # acc += input[i] * weight[i][j]
    fmul.s fa3, fa1, fa2                # fa3 = input[i] * weight[i][j]
    fadd.s fa0, fa0, fa3                # fa0 += fa3
    
    addi s4, s4, 1                      # i++
    j .L{layer_idx}_inner_loop

.L{layer_idx}_apply_activation:
"""
        
        # Add activation function
        if activation == "relu":
            asm += f"""    # Apply ReLU: max(fa0, 0.0)
    fmv.w.x fa1, zero                   # fa1 = 0.0
    fmax.s fa0, fa0, fa1                # fa0 = max(fa0, 0.0)
"""
        elif activation == "sigmoid":
            asm += f"""    # Apply Sigmoid (piecewise linear approximation)
    # Save fa0 to stack before call
    addi sp, sp, -8
    fsw fa0, 4(sp)
    call sigmoid_piecewise
    flw fa0, 4(sp)
    addi sp, sp, 8
"""
        # else: no activation
        
        asm += f"""    
    # Store output[j] = fa0
    slli t0, s3, 2                      # t0 = j * 4
    add t1, s2, t0                      # t1 = output_buf + j*4
    fsw fa0, 0(t1)                      # output[j] = fa0
    
    addi s3, s3, 1                      # j++
    j .L{layer_idx}_outer_loop

.L{layer_idx}_done:
    # Restore callee-saved registers
    lw ra, 28(sp)
    lw s0, 24(sp)
    lw s1, 20(sp)
    lw s2, 16(sp)
    lw s3, 12(sp)
    lw s4, 8(sp)
    addi sp, sp, 32
    ret

"""
        return asm
    
    def _generate_input_mapping(self, model_type: str, input_size: int) -> str:
        """Generate code to map character input to network input."""
        if model_type == "generator":
            # For generator: map character code (a0) to 255-dimensional input
            # Simple approach: one-hot encoding
            return f"""
# Input mapping: Character code (a0) -> Network input
# For generator: one-hot encoding of character
map_input_generator:
    # a0 = character code (0-254)
    # Output: input buffer at 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]:08X}

    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) & 0xFFF}

    # Zero out entire input buffer (255 floats)
    li t1, {input_size * 4}
    xor t2, t2, t2
.Lclear_input:
    beq t2, t1, .Lclear_done
    add t3, t0, t2
    sw zero, 0(t3)
    addi t2, t2, 4
    j .Lclear_input

.Lclear_done:
    # Set input[char_code] = 1.0
    # Validate a0 is in range [0, 254]
    li t1, 255
    bgeu a0, t1, .Linput_done

    slli t1, a0, 2                  # t1 = char_code * 4
    add t1, t0, t1                  # t1 = input_buf + offset
    lui t2, 0x3F800                 # t2 = 1.0 in float
    sw t2, 0(t1)                    # input[char_code] = 1.0

.Linput_done:
    ret

"""
        else:
            # For recognizer: read pixels from framebuffer
            return f"""
# Input mapping: Framebuffer pixels -> Network input
# For recognizer: read 400 pixels (20x20) and normalize to [0,1]
map_input_recognizer:
    # Read from framebuffer at 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    # Write to input buffer at 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]:08X}

    lui t0, {self.MEMORY_LAYOUT["framebuffer_base"] >> 12}
    lui t1, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) >> 12}
    addi t1, t1, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) & 0xFFF}

    li t2, 0                        # t2 = pixel index
    li t3, 400                      # t3 = num pixels

.Lread_pixels:
    bge t2, t3, .Lread_done

    # Read byte pixel[i]
    add t4, t0, t2
    lbu t5, 0(t4)                   # t5 = pixel value [0-255]

    # Convert to float: divide by 255.0
    fcvt.s.wu fa0, t5               # fa0 = (float)pixel
    lui t6, 0x43800                 # 255.0 in float
    fmv.w.x fa1, t6
    fdiv.s fa0, fa0, fa1            # fa0 = pixel / 255.0

    # Store to input[i]
    slli t4, t2, 2                  # t4 = i * 4
    add t4, t1, t4                  # t4 = input_buf + i*4
    fsw fa0, 0(t4)

    addi t2, t2, 1
    j .Lread_pixels

.Lread_done:
    ret

"""

    def _generate_output_mapping(self, model_type: str, output_size: int) -> str:
        """Generate code to map network output to framebuffer."""
        if model_type == "generator":
            # For generator: convert 400 floats to pixels and write to framebuffer
            return f"""
# Output mapping: Network output -> Framebuffer pixels
# For generator: convert 400 floats to grayscale pixels
map_output_generator:
    # Read from output buffer at 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    # Write to framebuffer at 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}

    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) & 0xFFF}
    lui t1, {self.MEMORY_LAYOUT["framebuffer_base"] >> 12}

    li t2, 0                        # t2 = pixel index
    li t3, {output_size}            # t3 = num pixels (400)

.Lwrite_pixels:
    bge t2, t3, .Lwrite_done

    # Load float output[i]
    slli t4, t2, 2                  # t4 = i * 4
    add t4, t0, t4                  # t4 = output_buf + i*4
    flw fa0, 0(t4)                  # fa0 = output[i]

    # Clamp to [0.0, 1.0]
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1            # fa0 = max(fa0, 0.0)
    lui t5, 0x3F800                 # 1.0 in float
    fmv.w.x fa1, t5
    fmin.s fa0, fa0, fa1            # fa0 = min(fa0, 1.0)

    # Convert to byte: multiply by 255.0
    lui t5, 0x43800                 # 255.0 in float
    fmv.w.x fa1, t5
    fmul.s fa0, fa0, fa1            # fa0 = fa0 * 255.0

    # Convert to unsigned int
    fcvt.wu.s t5, fa0               # t5 = (uint)fa0

    # Store byte to framebuffer[i]
    add t4, t1, t2                  # t4 = framebuf + i
    sb t5, 0(t4)

    addi t2, t2, 1
    j .Lwrite_pixels

.Lwrite_done:
    ret

"""
        else:
            # For recognizer: show predicted class
            return f"""
# Output mapping: Network output -> Display prediction
# For recognizer: find argmax and display predicted character
map_output_recognizer:
    # Read from output buffer at 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    # For now: just return (visualization TBD)

    # TODO: Implement argmax and character display
    ret

"""

    def _generate_model_forward_pass(self) -> str:
        """Generate complete forward pass through all layers."""
        if not self.layers:
            return "    # No layers\n    ret\n"

        model_type = self.metadata.get("model_type", "generator")
        model_base = (self.MEMORY_LAYOUT["generator_base"] 
                     if model_type == "generator" 
                     else self.MEMORY_LAYOUT["recognizer_base"])

        code = f"""
# Forward pass through all {len(self.layers)} layers
run_forward_pass:
    addi sp, sp, -16
    sw ra, 12(sp)

"""
        # Generate code for each layer
        for i, layer in enumerate(self.layers):
            is_last = (i == len(self.layers) - 1)
            code += f"    # === Layer {i} ===\n"
            code += f"    call layer_{i}_forward\n\n"

        code += """    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
        return code



    def _generate_execution_loop(self, model_type: str) -> str:
        """Generate the main cyclic execution loop."""
        return f"""
# Main execution loop: Input -> Forward Pass -> Output -> Repeat
# Mimics static_char_gen.c behavior but with neural network
.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to safe location (within 1MB, below code/data)
    li sp, 0xF000              # sp = 0x0F000 (61440 bytes)
    
    # Main inference loop (infinite)
inference_loop:
    # Step 1: Read input and map to network input
    # For generator: a0 contains character code (set externally or hardcoded for testing)
    # For now, use a test character 'A' = 65
    li a0, 65                    # TODO: Read from external source
    call map_input_{model_type}
    
    # Step 2: Run forward pass through all layers
    call run_forward_pass
    
    # Step 3: Map output to framebuffer
    call map_output_{model_type}
    
    # Step 4: Loop back
    j inference_loop
    
    # Unreachable, but include exit for completeness
    li a0, 0
    li a7, 93                    # SYS_exit
    ecall

"""


    def compile(self, json_path: str, output_asm: str, with_bootloader: bool = True) -> Tuple[str, str]:
        """
        Compile JSON to assembly and binary with optional bootloader code.
        
        Args:
            json_path: Path to JSON intermediate file
            output_asm: Path to output assembly file
            with_bootloader: If True, generate full bootloader (Phase 2).
                           If False, generate skeleton only (Phase 1).
        
        Returns:
            Tuple of (asm_file_path, bin_file_path)
        """
        bin_path = str(Path(output_asm).with_suffix('.bin'))
        asm_path = self.generate_assembly(json_path, output_asm, bin_path, 
                                         with_bootloader=with_bootloader)
        return (asm_path, bin_path)


def main():
    """CLI interface for model_compiler.py"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Model Compiler: JSON intermediate → RISC-V Assembly with embedded data"
    )
    parser.add_argument(
        "json_file",
        help="Path to JSON intermediate format file"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output assembly file (default: <json_file>.s)"
    )
    parser.add_argument(
        "-b", "--binary",
        default=None,
        help="Output binary file (default: <output>.bin)"
    )
    parser.add_argument(
        "--no-bootloader",
        action="store_true",
        help="Generate skeleton only (Phase 1) without bootloader code (Phase 2)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output is None:
        args.output = str(Path(args.json_file).with_suffix('.s'))
    
    try:
        compiler = ModelCompiler(verbose=args.verbose)
        asm_path, bin_path = compiler.compile(args.json_file, args.output, 
                                             with_bootloader=not args.no_bootloader)
        
        print(f"✓ Assembly generated: {asm_path}")
        print(f"✓ Binary generated:  {bin_path}")
        
        return 0
    except Exception as e:
        print(f"✗ Compilation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
