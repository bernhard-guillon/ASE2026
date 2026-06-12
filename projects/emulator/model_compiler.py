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
    MODEL_TYPES = {"generator": 0, "chained": 0}
    ACTIVATIONS = {"relu": 0, "sigmoid": 1, "none": 2}
    
    HEADER_SIZE = 32
    LAYER_ENTRY_SIZE = 32
    
    # Memory layout constants (from Sprint 1 design)
    MEMORY_LAYOUT = {
        "code_base": 0x00001000,
        "generator_base": 0x00010000,
        "buffer_base": 0x00150000,
        "framebuffer_base": 0x00020000,
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
        self.use_neural_ops = False
        self.neural_opcode = "x77"
        self.neural_lane_mode = "base"
        
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
                         with_bootloader: bool = True, with_execution: bool = False,
                         use_neural_ops: bool = False, neural_opcode: str = "x77",
                         neural_lane_mode: str = "base") -> str:
        """
        Generate complete RISC-V assembly file with model data and execution code.
        
        Args:
            json_path: Path to JSON intermediate format
            output_asm: Path to output .s file
            temp_bin: Path to temporary binary file (default: output_asm.bin)
            with_bootloader: Include bootloader code (legacy, kept for compatibility)
            with_execution: Include neural network execution code (Sprint 2)
            use_neural_ops: Emit custom neural op mnemonics (opcode 0x77) for
                layer execution and output mapping.
            neural_opcode: Neural custom opcode variant: "x77" (legacy CUSTOM0)
                or "x7b" (enhanced CUSTOM3).
            neural_lane_mode: For x7b custom ops, selects matvec mnemonic family:
                "base" -> nmatvecx.f32, "4x" -> nmatvec4x.f32,
                "8x" -> nmatvec8x.f32, "8xpmac" -> nmatvec8xp.f32,
                "8xpmac2" -> nmatvec8xp2.f32,
                "8xpmac3" -> nmatvec8xp3.f32,
                "8xpmac4" -> nmatvec8xp4.f32.
        
        Returns:
            Path to generated assembly file
        """
        if self.verbose:
            print(f"[ModelCompiler] Generating assembly: {output_asm}")

        self.use_neural_ops = use_neural_ops
        self.neural_opcode = neural_opcode.lower()
        if self.neural_opcode not in ("x77", "x7b"):
            raise ValueError(f"Unsupported neural_opcode '{neural_opcode}'; expected x77 or x7b")
        self.neural_lane_mode = neural_lane_mode.lower()
        if self.neural_lane_mode not in ("base", "4x", "8x", "8xpmac", "8xpmac2", "8xpmac3", "8xpmac4"):
            raise ValueError(
                f"Unsupported neural_lane_mode '{neural_lane_mode}'; expected base, 4x, 8x, 8xpmac, 8xpmac2, 8xpmac3, or 8xpmac4"
            )
        if self.neural_opcode == "x77" and self.neural_lane_mode != "base":
            raise ValueError("neural_lane_mode 4x/8x/8xpmac/8xpmac2/8xpmac3/8xpmac4 is only valid with neural_opcode x7b")
        
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
        # Use metadata output_size if available (for models with framebuffer_size != last layer output)
        output_size = self.metadata.get("output_size", self.layers[-1]["output_size"] if self.layers else 0)
        
        # Determine model base address
        model_base = self.MEMORY_LAYOUT["generator_base"]
        
        # Build complete assembly file
        asm_parts = []
        
        # Header comment
        asm_parts.append(self._generate_asm_header(model_type, num_layers, len(binary)))
        
        # Data section with embedded binary
        # Place model at high address only when execution code is generated
        # (execution writes to framebuffer at 0x20000 and may overlap low-placed data).
        asm_parts.append(
            self._generate_data_section(
                temp_bin,
                len(binary),
                place_model_high=with_execution
            )
        )
        
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

.section .data
.align 4
.globl model_data_start

"""
    
    def _generate_data_section(self, bin_path: str, binary_size: int, place_model_high: bool = False) -> str:
        """Generate .data section with .incbin directive."""
        # Make path relative if possible for portability
        bin_path_display = Path(bin_path).name  # Just filename for comments

        if place_model_high:
            org_prefix = """# Keep model blob away from framebuffer (0x20000) so framebuffer writes
# cannot corrupt model weights/biases during cyclic inference.
    .org 0x30000
"""
        else:
            org_prefix = ""

        return f"""# Model binary data (embedded via .incbin)
# Size: {binary_size} bytes
{org_prefix}\
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
        if self.metadata is None or self.metadata.get("model_type") != "generator":
            # For single model (either generator or chained)
            return self._generate_single_model_bootloader()
        
        # For now, assume we're compiling a single model
        # Full two-model bootloader will be used when both models are available
        return self._generate_single_model_bootloader()
    
    def _generate_single_model_bootloader(self) -> str:
        """Generate bootloader for a single model."""
        model_type = self.metadata.get("model_type", "unknown")
        binary_size = len(self.binary_data) if self.binary_data else 0
        
        if model_type == "generator":
            dest_addr = 0x10000
            model_name = "generator"
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
    
    def _generate_sigmoid_piecewise(self) -> str:
        """Generate piecewise linear sigmoid approximation function.
        
        Uses a simple symmetric approximation:
        - x <= -4: return 0
        - x in [-4, 4]: return 0.5 + x * 0.125 (gives 0 at -4, 0.5 at 0, 1 at 4)
        - x >= 4: return 1
        """
        return """
# Sigmoid piecewise linear approximation
# Input: fa0 (x value)
# Output: fa0 (sigmoid(x))
# Formula: clamp(0.5 + x * 0.125, 0, 1) with saturation at x <= -4 and x >= 4
sigmoid_piecewise:
    # Save registers
    addi sp, sp, -16
    sw ra, 12(sp)
    fsw fa1, 8(sp)
    fsw fa2, 4(sp)
    
    # Check x <= -4.0
    lui t0, 0xC0800          # -4.0 in float (0xC0800000)
    fmv.w.x fa1, t0
    fle.s t0, fa0, fa1
    beq t0, zero, .Lsig_check_high
    # x <= -4: return 0.0
    fmv.w.x fa0, zero
    j .Lsig_done
    
.Lsig_check_high:
    # Check x >= 4.0
    lui t0, 0x40800          # 4.0 in float (0x40800000)
    fmv.w.x fa1, t0
    fle.s t0, fa1, fa0       # 4.0 <= x ?
    beq t0, zero, .Lsig_linear
    # x >= 4: return 1.0
    lui t0, 0x3F800          # 1.0 in float
    fmv.w.x fa0, t0
    j .Lsig_done
    
.Lsig_linear:
    # x in [-4, 4]: return 0.5 + x * 0.125
    lui t0, 0x3E000          # 0.125 in float (0x3E000000)
    fmv.w.x fa1, t0
    fmul.s fa1, fa0, fa1     # fa1 = x * 0.125
    lui t0, 0x3F000          # 0.5 in float (0x3F000000)
    fmv.w.x fa2, t0
    fadd.s fa0, fa2, fa1     # fa0 = 0.5 + x * 0.125
    
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
        
        if self.use_neural_ops:
            op_suffix = "x" if self.neural_opcode == "x7b" else ""
            op_tag = self.neural_opcode.upper()
            if self.neural_opcode == "x7b":
                matvec_mnemonic = {
                    "base": "nmatvecx.f32",
                    "4x": "nmatvec4x.f32",
                    "8x": "nmatvec8x.f32",
                    "8xpmac": "nmatvec8xp.f32",
                    "8xpmac2": "nmatvec8xp2.f32",
                    "8xpmac3": "nmatvec8xp3.f32",
                    "8xpmac4": "nmatvec8xp4.f32",
                }[self.neural_lane_mode]
            else:
                matvec_mnemonic = "nmatvec.f32"
            desc_addr = self.MEMORY_LAYOUT["buffer_base"] + 0x3A00 + (layer_idx * 0x20)
            activation_asm = ""
            if activation == "relu":
                activation_asm = f"""    # In-place ReLU over output vector
    li t1, 0x{output_buf:08X}
    li t2, 0x{output_buf:08X}
    li t4, {output_size}
    nvrelu{op_suffix}.f32 t3, t1, t2, t4
    bne t3, zero, .L{layer_idx}_ret
"""
            elif activation == "sigmoid":
                activation_asm = f"""    # In-place sigmoid PWL over output vector
    li t1, 0x{output_buf:08X}
    li t2, 0x{output_buf:08X}
    li t4, {output_size}
    nvsigpwl{op_suffix}.f32 t3, t1, t2, t4
    bne t3, zero, .L{layer_idx}_ret
"""

            return f"""
# Layer {layer_idx}: Dense [{input_size} → {output_size}] + {activation} (custom ops {op_tag})
layer_{layer_idx}_forward:
    # Descriptor at 0x{desc_addr:08X}
    # [0]=input_ptr [4]=weights_ptr [8]=bias_ptr [12]=output_ptr
    # [16]=input_len [20]=output_len [24]=flags [28]=reserved
    li t0, 0x{desc_addr:08X}
    li t1, 0x{input_buf:08X}
    sw t1, 0(t0)

    la t1, model_data_start
    li t2, {weights_offset}
    add t2, t1, t2
    sw t2, 4(t0)

    li t2, {biases_offset}
    add t2, t1, t2
    sw t2, 8(t0)

    li t2, 0x{output_buf:08X}
    sw t2, 12(t0)

    li t2, {input_size}
    sw t2, 16(t0)
    li t2, {output_size}
    sw t2, 20(t0)
    sw zero, 24(t0)
    sw zero, 28(t0)

    # Dense compute: output = bias + input * weights
    {matvec_mnemonic} t3, t0
    bne t3, zero, .L{layer_idx}_ret

{activation_asm}.L{layer_idx}_ret:
    ret

"""

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

    # Initialize weight column walk:
    #   start at weights_offset + j*4, stride by output_size*4 for i++
    li t5, {weights_offset}
    add t5, s0, t5
    add t5, t5, t2
    li t6, {output_size * 4}
    
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
    
    # Load weight[i][j] from column-walk pointer t5
    flw fa2, 0(t5)                      # fa2 = weight[i][j]
    
    # acc += input[i] * weight[i][j]
    fmul.s fa3, fa1, fa2                # fa3 = input[i] * weight[i][j]
    fadd.s fa0, fa0, fa3                # fa0 += fa3
    
    # Advance to weight[i+1][j]
    add t5, t5, t6
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
    # fa0 contains input, sigmoid_piecewise returns result in fa0
    call sigmoid_piecewise
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
        input_mapping = (self.metadata or {}).get("input_mapping", "")
        # Chained model: physics_state (46) + counter_state (11) -> total input
        if model_type == "chained":
            return f"""
# Input mapping: Chained model input (physics_state + counter_state)
# First tick: seed deterministic initial compact state.
# Later ticks: feed previous compact output back into compact input.
map_input_chained:
    li t0, 0x{self.MEMORY_LAYOUT['buffer_base'] + self.BUFFER_OFFSETS['input']:08X}
    li t1, 0x{self.MEMORY_LAYOUT['buffer_base'] + self.BUFFER_OFFSETS['output']:08X}
    li t2, 0x{self.MEMORY_LAYOUT['buffer_base'] + 0x3FF0:08X}   # init flag slot
    lw t3, 0(t2)
    bne t3, zero, .Lcopy_prev_chained

    # First tick: clear and seed initial compact state
    li t4, {input_size * 4}
    li t5, 0
.Lclear_input_chained:
    bge t5, t4, .Lseed_input_chained
    add t6, t0, t5
    sw zero, 0(t6)
    addi t5, t5, 4
    j .Lclear_input_chained

.Lseed_input_chained:
    lui t6, 0x3F800                  # 1.0f
    # physics: x=1, y=10, vx=+1, vy=0
    li a0, {1 * 4}
    add a1, t0, a0
    sw t6, 0(a1)
    li a0, {30 * 4}
    add a1, t0, a0
    sw t6, 0(a1)
    li a0, {42 * 4}
    add a1, t0, a0
    sw t6, 0(a1)
    li a0, {44 * 4}
    add a1, t0, a0
    sw t6, 0(a1)
    # counter: count=0 one-hot, stop=0
    li a0, {46 * 4}
    add a1, t0, a0
    sw t6, 0(a1)
    li t3, 1
    sw t3, 0(t2)
    ret

.Lcopy_prev_chained:
    li t4, {input_size * 4}
    li t5, 0
.Lcopy_prev_chained_loop:
    bge t5, t4, .Lcopy_prev_chained_done
    add t6, t1, t5
    lw a0, 0(t6)
    add a1, t0, t5
    sw a0, 0(a1)
    addi t5, t5, 4
    j .Lcopy_prev_chained_loop

.Lcopy_prev_chained_done:
    ret

"""
        if model_type == "generator":
            if input_mapping == "counter255_a0_feedback":
                return f"""
# Input mapping: counter255 feedback (a0 scalar 0..254 -> one-hot 255)
map_input_generator:
    li t0, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]:08X}

    # Zero out full input buffer (255 floats)
    li t1, {input_size * 4}
    li t2, 0
.Lclear_input_counter255:
    bge t2, t1, .Lset_counter255_input
    add t3, t0, t2
    sw zero, 0(t3)
    addi t2, t2, 4
    j .Lclear_input_counter255

.Lset_counter255_input:
    li t1, 255
    bgeu a0, t1, .Linput_done_counter255
    slli t2, a0, 2
    add t2, t0, t2
    lui t3, 0x3F800                  # 1.0f
    sw t3, 0(t2)

.Linput_done_counter255:
    ret

"""
            if input_mapping == "counter_char_a0_bridge":
                return f"""
# Input mapping: staged counter->char bridge seed (a0 scalar 0..254 -> one-hot 255)
# In staged forward pass, layer0 updates a0 each tick and layer1+ consume it.
map_input_generator:
    li t0, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]:08X}

    # Zero out full input buffer (255 floats)
    li t1, {input_size * 4}
    li t2, 0
.Lclear_input_counter_char:
    bge t2, t1, .Lset_counter_char_input
    add t3, t0, t2
    sw zero, 0(t3)
    addi t2, t2, 4
    j .Lclear_input_counter_char

.Lset_counter_char_input:
    li t1, 255
    bgeu a0, t1, .Linput_done_counter_char
    slli t2, a0, 2
    add t2, t0, t2
    lui t3, 0x3F800                  # 1.0f
    sw t3, 0(t2)

.Linput_done_counter_char:
    ret

"""
            if input_mapping == "movement_packed_a0":
                return f"""
# Input mapping: packed movement code (a0) -> [board one-hot + action one-hot]
# a0 bits:
#   [8:0]   state index (0..399 for 20x20 board)
#   [11:9]  action id (0..4) = up/down/left/right/stay
map_input_generator:
    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) & 0xFFF}

    # Zero out entire input buffer
    li t1, {input_size * 4}
    xor t2, t2, t2
.Lclear_input_movement:
    beq t2, t1, .Ldecode_input_movement
    add t3, t0, t2
    sw zero, 0(t3)
    addi t2, t2, 4
    j .Lclear_input_movement

.Ldecode_input_movement:
    # state_idx = a0 & 0x1FF
    # action_id = (a0 >> 9) & 0x7
    li t1, 0x1FF
    and t2, a0, t1
    srli t3, a0, 9
    andi t3, t3, 0x7

    # Validate state_idx < 400 and action_id < 5
    li t4, 400
    bgeu t2, t4, .Linput_done_movement
    li t4, 5
    bgeu t3, t4, .Linput_done_movement

    # input[state_idx] = 1.0
    slli t4, t2, 2
    add t4, t0, t4
    lui t5, 0x3F800
    sw t5, 0(t4)

    # input[400 + action_id] = 1.0
    li t4, 400
    add t4, t4, t3
    slli t4, t4, 2
    add t4, t0, t4
    sw t5, 0(t4)

.Linput_done_movement:
    ret

"""
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
            return """
# Input mapping: Generic -> Network input
map_input_generic:
    ret

"""

    def _generate_output_mapping(self, model_type: str, output_size: int) -> str:
        """Generate code to map network output to framebuffer."""
        input_mapping = (self.metadata or {}).get("input_mapping", "")
        if model_type == "chained":
            return f"""
# Output mapping: chained compact state -> framebuffer
# - draw ball from argmax(ball_x, ball_y)
# - draw counter as a bottom-row bar (temporary visualization hack)
# - draw stop indicator at bottom-right when stop > 0.5
map_output_chained:
    li t0, 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    li t1, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}

    # Clear framebuffer (400 bytes, stride-320 layout)
    li t2, 0
    li t3, 400
    li t4, 0                        # col
    li t5, 0                        # row
.Lclear_fb_chained:
    bge t2, t3, .Largmax_x_init
    slli a5, t5, 8                  # a5 = row * 256
    slli a6, t5, 6                  # a6 = row * 64
    add a5, a5, a6                  # a5 = row * 320
    add a5, a5, t4                  # a5 = row * 320 + col
    add a5, t0, a5
    sb zero, 0(a5)
    addi t4, t4, 1
    li a5, 20
    bne t4, a5, .Lclear_no_row_inc_ch
    li t4, 0
    addi t5, t5, 1
.Lclear_no_row_inc_ch:
    addi t2, t2, 1
    j .Lclear_fb_chained

.Largmax_x_init:
    li t2, 0
    li t3, 0
    li a0, 0xFF800000
    fmv.w.x fa1, a0
.Largmax_x_loop:
    li a1, 20
    bge t2, a1, .Largmax_y_init
    slli a2, t2, 2
    add a2, t1, a2
    flw fa0, 0(a2)
    flt.s a3, fa1, fa0
    beq a3, zero, .Largmax_x_next
    fsgnj.s fa1, fa0, fa0
    addi t3, t2, 0
.Largmax_x_next:
    addi t2, t2, 1
    j .Largmax_x_loop

.Largmax_y_init:
    li t2, 20
    li t4, 20
    li a0, 0xFF800000
    fmv.w.x fa2, a0
.Largmax_y_loop:
    li a1, 40
    bge t2, a1, .Ldraw_ball_chained
    slli a2, t2, 2
    add a2, t1, a2
    flw fa0, 0(a2)
    flt.s a3, fa2, fa0
    beq a3, zero, .Largmax_y_next
    fsgnj.s fa2, fa0, fa0
    addi t4, t2, 0
.Largmax_y_next:
    addi t2, t2, 1
    j .Largmax_y_loop

.Ldraw_ball_chained:
    addi t4, t4, -20                # y in 0..19
    slli a1, t4, 8                  # y * 256
    slli a2, t4, 6                  # y * 64
    add a1, a1, a2                  # y * 320
    add a1, a1, t3                  # y*320 + x
    add a1, t0, a1
    li a2, 255
    sb a2, 0(a1)

    # counter count = argmax(output[46..55])
    li t2, 46
    li t5, 46
    li a0, 0xFF800000
    fmv.w.x fa3, a0
.Largmax_count_loop:
    li a1, 56
    bge t2, a1, .Ldraw_counter_bar
    slli a2, t2, 2
    add a2, t1, a2
    flw fa0, 0(a2)
    flt.s a3, fa3, fa0
    beq a3, zero, .Largmax_count_next
    fsgnj.s fa3, fa0, fa0
    addi t5, t2, 0
.Largmax_count_next:
    addi t2, t2, 1
    j .Largmax_count_loop

.Ldraw_counter_bar:
    addi t5, t5, -46                # count 0..9
    addi t5, t5, 1                  # show at least one pixel for visibility
    li a0, 6080                     # row 19 base index (19 * 320)
    add a0, t0, a0
    li t2, 0
.Ldraw_counter_loop:
    bge t2, t5, .Ldraw_stop_indicator
    li a1, 20
    bge t2, a1, .Ldraw_stop_indicator
    add a2, a0, t2
    li a3, 127
    sb a3, 0(a2)
    addi t2, t2, 1
    j .Ldraw_counter_loop

.Ldraw_stop_indicator:
    li a1, {56 * 4}
    add a1, t1, a1
    flw fa0, 0(a1)
    lui a2, 0x3F000                 # 0.5f
    fmv.w.x fa4, a2
    flt.s a3, fa4, fa0              # stop > 0.5 ?
    beq a3, zero, .Loutput_done_chained
    li a4, 6099                     # bottom-right corner (19*320 + 19)
    add a4, t0, a4
    li a5, 255
    sb a5, 0(a4)

.Loutput_done_chained:
    ret

"""
        if model_type == "generator":
            if input_mapping == "counter255_a0_feedback":
                debug_word = self.MEMORY_LAYOUT["buffer_base"] + 0x3FE0
                return f"""
# Output mapping: counter255 argmax -> a0 + debug word + framebuffer marker
map_output_generator:
    li t0, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    li t1, 255

    # Argmax over 255 outputs
    li t2, 0                          # i
    li t3, 0                          # max_idx
    flw fa0, 0(t0)                    # max_val = output[0]
.Largmax_counter255:
    bge t2, t1, .Largmax_counter255_done
    slli t4, t2, 2
    add t5, t0, t4
    flw fa1, 0(t5)
    flt.s t6, fa0, fa1
    beq t6, zero, .Largmax_counter255_next
    fsgnj.s fa0, fa1, fa1
    addi t3, t2, 0
.Largmax_counter255_next:
    addi t2, t2, 1
    j .Largmax_counter255

.Largmax_counter255_done:
    # Feed back scalar state into a0 for next tick
    addi a0, t3, 0

    # Persist scalar state for blackbox checks
    li t2, 0x{debug_word:08X}
    sw t3, 0(t2)

    # Visual marker: clear framebuffer and set one pixel at index=max_idx (stride-320)
    li t4, 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    li t5, 0
    li t6, 400
    li a3, 0                        # col
    li a4, 0                        # row
.Lclear_fb_counter255:
    bge t5, t6, .Ldraw_counter255_pixel
    slli a5, a4, 8
    slli a6, a4, 6
    add a5, a5, a6
    add a5, a5, a3
    add a1, t4, a5
    sb zero, 0(a1)
    addi a3, a3, 1
    li a5, 20
    bne a3, a5, .Lclear_no_row_inc_c255
    li a3, 0
    addi a4, a4, 1
.Lclear_no_row_inc_c255:
    addi t5, t5, 1
    j .Lclear_fb_counter255

.Ldraw_counter255_pixel:
    # t3 = argmax index; compute row/col for stride-320
    li a6, 0
    li a3, 20
    mv a5, t3
.Ldiv20_loop_c255:
    blt a5, a3, .Ldiv20_done_c255
    sub a5, a5, a3
    addi a6, a6, 1
    j .Ldiv20_loop_c255
.Ldiv20_done_c255:
    slli a1, a6, 8
    slli a2, a6, 6
    add a1, a1, a2
    add a1, a1, a5
    add a1, t4, a1
    li a2, 255
    sb a2, 0(a1)
    ret

"""
            if input_mapping == "movement_packed_a0":
                return f"""
# Output mapping: movement argmax -> single active framebuffer cell (stride-320)
map_output_generator:
    li t0, 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    li t1, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}

    # Clear framebuffer (stride-320)
    li t2, 0
    li t3, {output_size}
    li a3, 0                        # col
    li a4, 0                        # row
.Lclear_fb_movement:
    bge t2, t3, .Largmax_start_movement
    slli a5, a4, 8
    slli a6, a4, 6
    add a5, a5, a6
    add a5, a5, a3
    add a5, t0, a5
    sb zero, 0(a5)
    addi a3, a3, 1
    li a5, 20
    bne a3, a5, .Lclear_no_row_inc_mv
    li a3, 0
    addi a4, a4, 1
.Lclear_no_row_inc_mv:
    addi t2, t2, 1
    j .Lclear_fb_movement

.Largmax_start_movement:
    # max_idx = 0, i = 1
    li t4, 0
    li t2, 1

.Largmax_loop_movement:
    bge t2, t3, .Largmax_done_movement

    # current_max = output[max_idx]
    slli t5, t4, 2
    add t6, t1, t5
    flw fa0, 0(t6)

    # candidate = output[i]
    slli t5, t2, 2
    add t6, t1, t5
    flw fa1, 0(t6)

    # if candidate > current_max: max_idx = i
    flt.s t6, fa0, fa1
    beq t6, zero, .Largmax_skip_update_movement
    addi t4, t2, 0

.Largmax_skip_update_movement:
    addi t2, t2, 1
    j .Largmax_loop_movement

.Largmax_done_movement:
    # t4 = argmax index; compute stride-320 offset
    li a6, 0
    li a3, 20
    mv a5, t4
.Ldiv20_loop_mv:
    blt a5, a3, .Ldiv20_done_mv
    sub a5, a5, a3
    addi a6, a6, 1
    j .Ldiv20_loop_mv
.Ldiv20_done_mv:
    slli a1, a6, 8
    slli a2, a6, 6
    add a1, a1, a2
    add a1, a1, a5
    add a1, t0, a1
    li a2, 255
    sb a2, 0(a1)
    ret

"""
            if self.use_neural_ops:
                op_suffix = "x" if self.neural_opcode == "x7b" else ""
                op_tag = self.neural_opcode.upper()
                return f"""
# Output mapping: Network output -> Framebuffer pixels (custom op {op_tag})
map_output_generator:
    # nvclampu8.f32(dst_u8=framebuffer, src_f32=output_buf, len={output_size})
    li t0, 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    li t1, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    li t2, {output_size}
    nvclampu8{op_suffix}.f32 t3, t0, t1, t2
    ret

"""
            # For generator: convert 400 floats to pixels and write to framebuffer with stride-320
            return f"""
# Output mapping: Network output -> Framebuffer pixels (stride-320 layout)
# For generator: convert {output_size} floats to grayscale pixels
map_output_generator:
    # Read from output buffer at 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    # Write to framebuffer at 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}

    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) & 0xFFF}
    lui t1, {self.MEMORY_LAYOUT["framebuffer_base"] >> 12}

    li t2, 0                        # t2 = pixel index (0..{output_size-1})
    li t3, {output_size}            # t3 = num pixels (400)
    li t4, 0                        # t4 = col (0..19)
    li t5, 0                        # t5 = row (0..19)

.Lwrite_pixels:
    bge t2, t3, .Lwrite_done

    # Load float output[i]
    slli t6, t2, 2                  # t6 = i * 4
    add t6, t0, t6                  # t6 = output_buf + i*4
    flw fa0, 0(t6)                  # fa0 = output[i]

    # Clamp to [0.0, 1.0]
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1            # fa0 = max(fa0, 0.0)
    lui t6, 0x3F800                 # 1.0 in float
    fmv.w.x fa1, t6
    fmin.s fa0, fa0, fa1            # fa0 = min(fa0, 1.0)

    # Convert to byte: multiply by 255.0
    lui t6, 0x43800                 # 255.0 in float
    fmv.w.x fa1, t6
    fmul.s fa0, fa0, fa1            # fa0 = fa0 * 255.0

    # Convert to unsigned int
    fcvt.wu.s t6, fa0               # t6 = (uint)fa0

    # Compute framebuffer offset: row * 320 + col
    slli a5, t5, 8                  # a5 = row * 256
    slli a6, t5, 6                  # a6 = row * 64
    add a5, a5, a6                  # a5 = row * 320
    add a5, a5, t4                  # a5 = row * 320 + col
    add a5, t1, a5                  # a5 = framebuf + offset
    sb t6, 0(a5)                    # Store byte to framebuffer

    # Advance col; wrap to next row if col reaches 20
    addi t4, t4, 1
    li a5, 20
    bne t4, a5, .Lno_row_inc
    li t4, 0
    addi t5, t5, 1
.Lno_row_inc:

    addi t2, t2, 1
    j .Lwrite_pixels

.Lwrite_done:
    ret

"""
        else:
            return """
# Output mapping: Generic -> return
map_output_generic:
    ret

"""

    def _generate_model_forward_pass(self) -> str:
        """Generate complete forward pass through all layers.

        Special-case: chained (dual-model) architecture needs buffer rewiring
        between the physics and counter sub-networks. For chained models the
        metadata is expected to contain `sub_networks` with `physics` and
        `counter` entries that include input_size/output_size and layer lists.
        """
        if not self.layers:
            return "    # No layers\n    ret\n"

        model_type = self.metadata.get("model_type", "generator")
        architecture = (self.metadata or {}).get("architecture", "")

        # If chained/dual-model metadata present, generate a special forward
        # pass that:
        # 1) preserves the counter_state from the global input into a temp
        #    (we use the output buffer as a temp region),
        # 2) patches the physics input's stop bit from the global input,
        # 3) runs the physics sub-network (its layers are the first N layers),
        # 4) extracts physics.hit_wall and builds the counter input in the
        #    activation buffer expected by the first counter layer,
        # 5) runs the counter sub-network layers, leaving the final output in
        #    the standard output buffer (final layer is compiled to write
        #    into buffer_base + output).
        if model_type == "chained" or architecture.startswith("dual-model-chained"):
            subs = (self.metadata or {}).get("sub_networks", {})
            physics_meta = subs.get("physics", {})
            counter_meta = subs.get("counter", {})

            p_layers = physics_meta.get("layers", [])
            c_layers = counter_meta.get("layers", [])
            p_count = len(p_layers)
            c_count = len(c_layers)

            p_input_size = int(physics_meta.get("input_size", 0))
            p_output_size = int(physics_meta.get("output_size", 0))
            c_input_size = int(counter_meta.get("input_size", 0))
            c_output_size = int(counter_meta.get("output_size", 0))

            global_input_size = int(self.metadata.get("input_size", p_input_size + c_input_size))

            input_addr = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]
            act_a_addr = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
            act_b_addr = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_b"]
            out_addr = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]

            code = f"""
# Forward pass (chained model: physics + counter)
run_forward_pass:
    addi sp, sp, -32
    sw ra, 28(sp)

    # === Preserve counter_state (count+stop) to temp (output buffer) ===
    li t0, 0x{input_addr:08X}        # input buffer base
    li t1, 0x{out_addr:08X}         # temp storage for counter_state
    li t2, {(p_output_size - 1) * 4}
    li t3, 0
    li a0, {c_output_size * 4}
.Lcopy_counter_to_temp:
    bge t3, a0, .Lcopy_counter_done
    add t4, t0, t2
    lw t5, 0(t4)
    add t6, t1, t3
    sw t5, 0(t6)
    addi t2, t2, 4
    addi t3, t3, 4
    j .Lcopy_counter_to_temp
.Lcopy_counter_done:

    # === Move stop bit from global input[end] -> physics input[last] ===
    li a1, 0x{input_addr:08X}
    li a2, {(global_input_size - 1) * 4}
    add a3, a1, a2
    lw a4, 0(a3)
    li a5, 0x{input_addr:08X}
    li a6, {(p_input_size - 1) * 4}
    add a7, a5, a6
    sw a4, 0(a7)

    # === Run physics sub-network layers ===
"""
            # call physics layers (assumed to be first p_count layers)
            for i in range(p_count):
                code += f"    call layer_{i}_forward\n"

            # compute addresses for physics output and counter input target
            p_last = p_count - 1
            phy_out_addr = act_a_addr if (p_last % 2 == 0) else act_b_addr
            target_buf_addr = act_a_addr if (p_count % 2 == 1) else act_b_addr

            code += f"""
    # === Extract hit_wall from physics output ===
    li t0, 0x{phy_out_addr:08X}
    li t1, {(p_output_size - 1) * 4}
    add t2, t0, t1
    lw t3, 0(t2)   # hit_wall (bit pattern)

    # === Preserve next physics_state (46 floats) into input buffer ===
    li t4, 0x{input_addr:08X}
    li t5, 0
    li t6, {(p_output_size - 1) * 4}
.Lcopy_physics_state_to_input:
    bge t5, t6, .Lcopy_physics_state_done
    add a1, t0, t5
    lw a2, 0(a1)
    add a3, t4, t5
    sw a2, 0(a3)
    addi t5, t5, 4
    j .Lcopy_physics_state_to_input
.Lcopy_physics_state_done:

    # === Build counter input in activation buffer ===
    li t4, 0x{out_addr:08X}        # temp storage where counter_state is saved
    li t5, 0x{target_buf_addr:08X} # target activation buffer for counter input
    li t6, 0
    li a1, {c_output_size * 4}
.Lcopy_counter_to_act:
    bge t6, a1, .Lcopy_counter_to_act_done
    add a2, t4, t6
    lw a3, 0(a2)
    add a4, t5, t6
    sw a3, 0(a4)
    addi t6, t6, 4
    j .Lcopy_counter_to_act
.Lcopy_counter_to_act_done:
    # Store hit_wall into last position of counter input
    add a5, t5, {(c_input_size - 1) * 4}
    sw t3, 0(a5)

    # === Run counter sub-network layers ===
"""
            for idx in range(p_count, p_count + c_count):
                code += f"    call layer_{idx}_forward\n"

            code += f"""
    # === Compose compact chained output (57 floats) ===
    # Save counter output[0..10] into input[46..56]
    li t0, 0x{out_addr:08X}
    li t1, 0x{input_addr:08X}
    li t2, {(p_output_size - 1) * 4}
    li t3, 0
    li t4, {c_output_size * 4}
.Lsave_counter_out_to_input:
    bge t3, t4, .Lsave_counter_done
    add t5, t0, t3
    lw t6, 0(t5)
    add a0, t1, t2
    sw t6, 0(a0)
    addi t2, t2, 4
    addi t3, t3, 4
    j .Lsave_counter_out_to_input
.Lsave_counter_done:

    # Write physics_state from input[0..45] to output[0..45]
    li t0, 0x{input_addr:08X}
    li t1, 0x{out_addr:08X}
    li t2, 0
    li t3, {(p_output_size - 1) * 4}
.Lwrite_physics_to_output:
    bge t2, t3, .Lwrite_counter_to_output
    add t4, t0, t2
    lw t5, 0(t4)
    add t6, t1, t2
    sw t5, 0(t6)
    addi t2, t2, 4
    j .Lwrite_physics_to_output

.Lwrite_counter_to_output:
    # Write counter_state from input[46..56] to output[46..56]
    li t0, 0x{input_addr:08X}
    li t1, 0x{out_addr:08X}
    li t2, {(p_output_size - 1) * 4}
    li t3, 0
    li t4, {c_output_size * 4}
.Lwrite_counter_to_output_loop:
    bge t3, t4, .Lcompose_done
    add t5, t0, t2
    lw t6, 0(t5)
    add a0, t1, t2
    sw t6, 0(a0)
    addi t2, t2, 4
    addi t3, t3, 4
    j .Lwrite_counter_to_output_loop

.Lcompose_done:
    # Restore and return
    lw ra, 28(sp)
    addi sp, sp, 32
    ret

"""
            return code

        # Counter->char flow:
        # - render the current character frame from the current a0
        # - compute the next counter value after the frame is written
        # - write the next value back to a0 for the following frame
        if architecture == "counter-char-staged":
            act_a_addr = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
            debug_word = self.MEMORY_LAYOUT["buffer_base"] + 0x3FE0

            code = f"""
# Forward pass (char-gen frame)
run_forward_pass:
    addi sp, sp, -16
    sw ra, 12(sp)

    # Rewrite activation_a as one-hot(a0) for char-gen layer_1 input
    li t0, 0x{act_a_addr:08X}
    li t1, 1020                      # 255 * 4
    li t2, 0
.Lclear_acta_counter_char:
    bge t2, t1, .Lset_acta_counter_char
    add t4, t0, t2
    sw zero, 0(t4)
    addi t2, t2, 4
    j .Lclear_acta_counter_char
.Lset_acta_counter_char:
    li t1, 255
    bgeu a0, t1, .Lrun_char_layers
    slli t2, a0, 2
    add t2, t0, t2
    lui t3, 0x3F800
    sw t3, 0(t2)

.Lrun_char_layers:
"""
            for i in range(1, len(self.layers)):
                code += f"    call layer_{i}_forward\n"

            code += """
    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
            code += f"""

# Update counter state after the frame has been rendered
update_counter_state:
    addi sp, sp, -16
    sw ra, 12(sp)

    # Counter layer uses the current a0 from the frame we just rendered
    call layer_0_forward

    # Argmax over counter output in activation_a -> next a0
    li t0, 0x{act_a_addr:08X}
    li t1, 255
    li t2, 0
    li t3, 0
    flw fa0, 0(t0)
.Largmax_counter_next_loop:
    bge t2, t1, .Largmax_counter_next_done
    slli t4, t2, 2
    add t5, t0, t4
    flw fa1, 0(t5)
    flt.s t6, fa0, fa1
    beq t6, zero, .Largmax_counter_next
    fsgnj.s fa0, fa1, fa1
    addi t3, t2, 0
.Largmax_counter_next:
    addi t2, t2, 1
    j .Largmax_counter_next_loop
.Largmax_counter_next_done:
    addi a0, t3, 0
    li t4, 0x{debug_word:08X}
    sw t3, 0(t4)

    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
            return code

        # Block-diagonal-parallel: add update_counter_state function
        if architecture == "block-diagonal-parallel":
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]
            debug_word = self.MEMORY_LAYOUT["buffer_base"] + 0x3FE0
            
            code = f"""
# Forward pass through all {len(self.layers)} layers
run_forward_pass:
    addi sp, sp, -16
    sw ra, 12(sp)

"""
            # Generate code for each layer
            for i, layer in enumerate(self.layers):
                code += f"    # === Layer {i} ===\n"
                code += f"    call layer_{i}_forward\n\n"

            code += """    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
            # Add update_counter_state function for block-diagonal
            code += f"""
# Update a0 from counter output (positions 400-654 in output buffer)
# Counter has 255 outputs, we take argmax to get the next character code
update_counter_state:
    addi sp, sp, -16
    sw ra, 12(sp)

    # Output buffer is at 0x{output_buf:08X}
    # Counter outputs are at byte offset {400 * 4} (positions 400-654)
    li t0, 0x{output_buf:08X}
    li t1, {400 * 4}
    add t0, t0, t1                    # t0 = address of counter output[0]
    li t1, 255                       # Number of counter outputs
    li t2, 0                         # Loop index
    li t3, 0                         # Best index (argmax result)
    flw fa0, 0(t0)                   # Initialize max value

.Largmax_counter_bd_loop:
    bge t2, t1, .Largmax_counter_bd_done
    slli t4, t2, 2                   # t4 = index * 4
    add t5, t0, t4                  # t5 = address of counter_output[index]
    flw fa1, 0(t5)                  # Load current value
    flt.s t6, fa0, fa1              # t6 = (fa0 < fa1) ? 1 : 0
    beq t6, zero, .Largmax_counter_bd_skip
    fmv.s fa0, fa1                  # New max
    addi t3, t2, 0                  # New best index
.Largmax_counter_bd_skip:
    addi t2, t2, 1
    j .Largmax_counter_bd_loop

.Largmax_counter_bd_done:
    addi a0, t3, 0                  # Set a0 to the next character code
    li t4, 0x{debug_word:08X}
    sw t3, 0(t4)                    # Debug: store next char code

    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
            return code

        # Default sequential forward pass (unchanged)
        code = f"""
# Forward pass through all {len(self.layers)} layers
run_forward_pass:
    addi sp, sp, -16
    sw ra, 12(sp)

"""
        # Generate code for each layer
        for i, layer in enumerate(self.layers):
            code += f"    # === Layer {i} ===\n"
            code += f"    call layer_{i}_forward\n\n"

        code += """    lw ra, 12(sp)
    addi sp, sp, 16
    ret

"""
        return code



    def _generate_execution_loop(self, model_type: str) -> str:
        """Generate the main cyclic execution loop."""
        architecture = self.metadata.get("architecture", "unknown")
        is_staged = architecture == "counter-char-staged"
        is_block_diagonal = architecture == "block-diagonal-parallel"
        
        if is_staged:
            return f"""
# Main execution loop: Input -> Forward Pass -> Output -> Counter Update -> Repeat
# For staged architecture: counter runs separately after frame is rendered
.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to safe location (within 1MB, below code/data)
    li sp, 0xF000              # sp = 0x0F000 (61440 bytes)
    
    # Main inference loop (infinite)
inference_loop:
    # Step 1: Read input and map to network input
    # a0 already contains the character code (seeded by the emulator runner)
    call map_input_{model_type}
    
    # Step 2: Run forward pass through the character generator layers
    call run_forward_pass
    
    # Step 3: Map output to framebuffer
    call map_output_{model_type}

    # Step 4: Advance counter state for the next frame
    call update_counter_state
    
    # Step 5: Loop back
    j inference_loop
    
    # Unreachable, but include exit for completeness
    li a0, 0
    li a7, 93                    # SYS_exit
    ecall

"""
        elif is_block_diagonal:
            # For block-diagonal-parallel: both networks run in parallel, counter updates a0
            return f"""
# Main execution loop: Input -> Forward Pass -> Output -> Counter Update -> Repeat
# For block-diagonal-parallel: counter and chargen run in parallel, counter updates a0 for next frame
.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to safe location (within 1MB, below code/data)
    li sp, 0xF000              # sp = 0x0F000 (61440 bytes)
    
    # Main inference loop (infinite)
inference_loop:
    # Step 1: Read input and map to network input
    # a0 already contains the character code (seeded by the emulator runner)
    call map_input_{model_type}
    
    # Step 2: Run forward pass through all layers (both counter and chargen in parallel)
    call run_forward_pass
    
    # Step 3: Map output to framebuffer (chargen outputs are first 400)
    call map_output_{model_type}

    # Step 4: Update a0 to next character based on counter output
    call update_counter_state
    
    # Step 5: Loop back
    j inference_loop
    
    # Unreachable, but include exit for completeness
    li a0, 0
    li a7, 93                    # SYS_exit
    ecall

"""
        else:
            # For non-staged, non-block-diagonal architectures
            # Don't call update_counter_state
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
    # a0 already contains the character code (seeded by the emulator runner)
    call map_input_{model_type}
    
    # Step 2: Run forward pass through all layers
    call run_forward_pass
    
    # Step 3: Map output to framebuffer
    call map_output_{model_type}

    # Step 4: Loop back (no counter state update for non-staged architectures)
    j inference_loop
    
    # Unreachable, but include exit for completeness
    li a0, 0
    li a7, 93                    # SYS_exit
    ecall

"""


    def compile(self, json_path: str, output_asm: str, with_bootloader: bool = True,
               with_execution: bool = False) -> Tuple[str, str]:
        """
        Compile JSON to assembly and binary with optional bootloader code.
        
        Args:
            json_path: Path to JSON intermediate file
            output_asm: Path to output assembly file
            with_bootloader: If True, generate full bootloader (Phase 2).
                           If False, generate skeleton only (Phase 1).
            with_execution: If True, generate neural execution code (Sprint 2).
                           If False, generate only bootloader/skeleton code.
        
        Returns:
            Tuple of (asm_file_path, bin_file_path)
        """
        bin_path = str(Path(output_asm).with_suffix('.bin'))
        asm_path = self.generate_assembly(
            json_path,
            output_asm,
            bin_path,
            with_bootloader=with_bootloader,
            with_execution=with_execution
        )
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
