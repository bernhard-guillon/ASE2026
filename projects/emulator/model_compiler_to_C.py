#!/usr/bin/env python3
"""
Model Compiler to C: Converts JSON intermediate format to C file with embedded RISC-V assembly.

This compiler extends ModelCompiler to output .c files instead of .s files.
The C file wraps RISC-V assembly in __asm__ volatile blocks and embeds model data
as a const uint32_t array.

Phase 1 of bootloader pipeline - C version.
"""

import json
import struct
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np


class CModelCompiler:
    """C Code Generator - extends ModelCompiler to output C files."""
    
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
        self.verbose = verbose
        self.metadata = None
        self.layers = None
        self.binary_data = None
        self.use_neural_ops = False
        self.neural_opcode = "x77"
        self.neural_lane_mode = "base"

    def load_json_intermediate(self, json_path: str) -> Dict:
        """Load JSON intermediate format."""
        if self.verbose:
            print(f"[CModelCompiler] Loading JSON: {json_path}")
        
        with open(json_path, 'r') as f:
            intermediate = json.load(f)
        
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
        """Convert loaded JSON to binary format."""
        if self.metadata is None or self.layers is None:
            raise ValueError("No model loaded. Call load_json_intermediate() first")
        
        if self.verbose:
            print("[CModelCompiler] Generating binary format...")
        
        if self.metadata.get("precision") != "float32":
            raise ValueError("Only float32 precision supported")
        
        model_type_val = self.MODEL_TYPES[self.metadata.get("model_type")]
        
        num_layers = len(self.layers)
        total_weights = sum(layer["input_size"] * layer["output_size"] for layer in self.layers)
        total_biases = sum(layer["output_size"] for layer in self.layers)
        
        if self.verbose:
            print(f"  Total weights: {total_weights}")
            print(f"  Total biases: {total_biases}")
        
        binary_data = bytearray()
        
        header = struct.pack(
            '<IIIIII4B',
            self.MAGIC,
            self.VERSION,
            model_type_val,
            num_layers,
            total_weights,
            total_biases,
            0, 0, 0, 0
        )
        binary_data.extend(header)
        
        weight_offset = 0
        bias_offset = 0
        
        for layer in self.layers:
            activation_val = self.ACTIVATIONS[layer.get("activation", "none")]
            num_weights = layer["input_size"] * layer["output_size"]
            num_biases = layer["output_size"]
            
            entry = struct.pack(
                '<8I',
                layer["input_size"],
                layer["output_size"],
                activation_val,
                weight_offset * 4,
                bias_offset * 4,
                0, 0, 0
            )
            binary_data.extend(entry)
            
            weight_offset += num_weights
            bias_offset += num_biases
        
        for layer in self.layers:
            weights = np.array(layer["weights"], dtype=np.float32)
            binary_data.extend(weights.tobytes())
        
        for layer in self.layers:
            biases = np.array(layer["biases"], dtype=np.float32)
            binary_data.extend(biases.tobytes())
        
        self.binary_data = bytes(binary_data)
        
        if self.verbose:
            print(f"  Binary size: {len(self.binary_data)} bytes")
        
        return self.binary_data

    def _generate_c_model_data(self, binary: bytes, model_base: int) -> str:
        """Generate model data as a C array."""
        words = len(binary) // 4
        uint32_array = []
        for i in range(words):
            word = int.from_bytes(binary[i*4:(i+1)*4], byteorder='little', signed=False)
            uint32_array.append(f"0x{word:08X}U")
        
        array_str = ",\n    ".join(uint32_array)
        
        return f"""// Model data at address 0x{model_base:08X}
// Size: {len(binary)} bytes ({words} words)
const uint32_t model_data[{words}] __attribute__((aligned(4))) = {{
    {array_str}
}};

// Assembly to define model_data_start and model_data_end symbols
__asm__(".section .rodata\\n"
       ".globl model_data_start\\n"
       ".set model_data_start, model_data\\n"
       ".globl model_data_end\\n"
       ".set model_data_end, model_data + {words * 4}\\n"
       ".previous\\n");
"""

    def _generate_c_headers(self, model_type: str) -> str:
        """Generate C header with function declarations."""
        num_layers = len(self.layers) if self.layers else 0
        layer_decls = "\n".join(f"void layer_{i}_forward(void);" for i in range(num_layers))
        
        return f"""// Generated by model_compiler_to_C.py
// C interface to RISC-V neural network model
// Compile with: riscv64-elf-gcc -march=rv32if -mabi=ilp32f -nostdlib

// Basic type definitions (no stdint.h dependency)
typedef unsigned int uint32_t;

// Function declarations
void _start(void);
void inference_loop(void);
void map_input_{model_type}(void);
void run_forward_pass(void);
void map_output_{model_type}(void);

// For block-diagonal-parallel
void update_counter_state(void);

// Layer functions
{layer_decls}

"""

    def _generate_c_wrapped_asm(self, asm_code: str) -> str:
        """Wrap assembly code in __asm__ volatile blocks within C functions."""
        import re
        
        # Split into functions by label
        functions = {}
        current_func = None
        current_body = []
        
        for line in asm_code.split('\n'):
            # Check for function label (ends with :)
            label_match = re.match(r'^(\w+):$', line.strip())
            if label_match:
                if current_func:
                    functions[current_func] = current_body
                current_func = label_match.group(1)
                current_body = []
            elif current_func:
                current_body.append(line)
        
        if current_func:
            functions[current_func] = current_body
        
        # Generate C functions wrapping each assembly function
        c_parts = []
        for func_name, func_body in functions.items():
            # Skip empty functions
            if not func_body:
                continue
            
            c_parts.append(f"void {func_name}(void) {{")
            c_parts.append("    __asm__ volatile (")
            for line in func_body:
                stripped = line.strip()
                if stripped:
                    # Escape any quotes in the assembly
                    escaped = stripped.replace('"', '\\"')
                    c_parts.append(f'        "{escaped} \\n"')
                else:
                    c_parts.append('        "\\n"')
            c_parts.append("    );")
            c_parts.append("}")
            c_parts.append("")
        
        return '\n'.join(c_parts)

    def _generate_asm_section(self, asm_code: str) -> str:
        """Generate assembly code as a separate .text section."""
        return f"""
// Assembly code section
__asm__(
    ".text\n"
    "{asm_code}\n"
    ".previous\n"
);
"""

    def _generate_asm_content(self, model_type: str, input_size: int, output_size: int) -> str:
        """Generate assembly content (without .data/.text sections) using logic from ModelCompiler."""
        asm_parts = []
        
        architecture = self.metadata.get("architecture", "")
        is_block_diagonal = "block-diagonal" in architecture
        
        # Execution loop
        asm_parts.append(self._generate_execution_loop(model_type))
        
        # I/O mapping
        asm_parts.append(self._generate_input_mapping(model_type, input_size))
        asm_parts.append(self._generate_output_mapping(model_type, output_size))
        
        # Forward pass
        asm_parts.append(self._generate_model_forward_pass())
        
        # Layer functions
        model_base = self.MEMORY_LAYOUT["generator_base"]
        
        for i, layer in enumerate(self.layers):
            is_last = (i == len(self.layers) - 1)
            layer_code = self._generate_dense_layer_forward(i, layer, model_base, is_last)
            asm_parts.append(layer_code)
        
        # Helper functions
        asm_parts.append(self._generate_sigmoid_piecewise())
        
        return '\n'.join(asm_parts)

    def _generate_execution_loop(self, model_type: str) -> str:
        """Generate the main execution loop."""
        architecture = self.metadata.get("architecture", "")
        input_mapping = self.metadata.get("input_mapping", "")
        is_block_diagonal = "block-diagonal" in architecture
        
        if is_block_diagonal and architecture.endswith("-parallel"):
            # Block-diagonal parallel: update counter state after forward pass
            return f"""# Main execution loop for block-diagonal-parallel model
# Reads counter outputs (positions 400-654), takes argmax, updates a0
inference_loop:
    # Map input from a0
    call map_input_{model_type}
    
    # Run forward pass
    call run_forward_pass
    
    # Map output to framebuffer
    call map_output_{model_type}
    
    # Update counter state: read counter outputs, argmax -> a0
    call update_counter_state
    
    # Loop forever
    j inference_loop
"""
        
        # Standard execution loop
        return f"""# Main execution loop
inference_loop:
    # Map input from a0
    call map_input_{model_type}
    
    # Run forward pass
    call run_forward_pass
    
    # Map output to framebuffer
    call map_output_{model_type}
    
    # Loop forever
    j inference_loop
"""

    def _generate_input_mapping(self, model_type: str, input_size: int) -> str:
        """Generate code to map character input to network input."""
        input_mapping = self.metadata.get("input_mapping", "")
        
        if model_type == "generator":
            if input_mapping == "counter255_a0_feedback":
                return f"""# Input mapping: counter255 feedback (a0 scalar 0..254 -> one-hot 255)
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
    lui t3, 0x3F800
    sw t3, 0(t2)

.Linput_done_counter255:
    ret
"""
            # Default: one-hot encoding of character
            return f"""# Input mapping: Character code (a0) -> Network input
map_input_generator:
    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]) & 0xFFF}

    # Zero out entire input buffer
    li t1, {input_size * 4}
    xor t2, t2, t2
.Lclear_input:
    beq t2, t1, .Lclear_done
    add t3, t0, t2
    sw zero, 0(t3)
    addi t2, t2, 4
    j .Lclear_input

 .Lclear_done:
    li t1, {input_size}
    bgeu a0, t1, .Linput_done
    slli t1, a0, 2
    add t1, t0, t1
    lui t2, 0x3F800
    sw t2, 0(t1)

.Linput_done:
    ret
"""
        else:
            return """# Input mapping: Generic -> Network input
map_input_generic:
    ret
"""

    def _generate_output_mapping(self, model_type: str, output_size: int) -> str:
        """Generate code to map network output to framebuffer."""
        input_mapping = self.metadata.get("input_mapping", "")
        architecture = self.metadata.get("architecture", "")
        
        if model_type == "generator":
            if input_mapping == "counter255_a0_feedback":
                debug_word = self.MEMORY_LAYOUT["buffer_base"] + 0x3FE0
                return f"""# Output mapping: counter255 argmax -> a0 + debug
map_output_generator:
    li t0, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    li t1, 255

    # Argmax over 255 outputs
    li t2, 0
    li t3, 0
    flw fa0, 0(t0)
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
    addi a0, t3, 0
    li t2, 0x{debug_word:08X}
    sw t3, 0(t2)

    # Visual marker: clear and set one pixel (stride-320 layout)
    li t4, 0x{self.MEMORY_LAYOUT["framebuffer_base"]:08X}
    li t5, 0
    li t6, 400
    li a3, 0                        # col
    li a4, 0                        # row
.Lclear_fb_counter255:
    bge t5, t6, .Ldraw_counter255_pixel
    slli a5, a4, 8                  # a5 = row * 256
    slli a6, a4, 6                  # a6 = row * 64
    add a5, a5, a6                  # a5 = row * 320
    add a5, a5, a3                  # a5 = row * 320 + col
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
    # t3 = argmax index; compute stride-320 offset
    # Use repeated subtraction for division by 20 (rv32if has no divu/remu)
    li a6, 0                        # row counter
    li a3, 20                       # divisor
    mv a5, t3
.Ldiv20_loop:
    blt a5, a3, .Ldiv20_done
    sub a5, a5, a3
    addi a6, a6, 1
    j .Ldiv20_loop
.Ldiv20_done:
    # a6 = row, a5 = col
    slli a1, a6, 8                  # a1 = row * 256
    slli a2, a6, 6                  # a2 = row * 64
    add a1, a1, a2                  # a1 = row * 320
    add a1, a1, a5                  # a1 = row * 320 + col
    add a1, t4, a1
    li a2, 255
    sb a2, 0(a1)
    ret
"""
            # Default: convert floats to pixels with stride-320 layout
            return f"""# Output mapping: Network output -> Framebuffer pixels (stride-320 layout)
map_output_generator:
    lui t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) >> 12}
    addi t0, t0, {(self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]) & 0xFFF}
    lui t1, {self.MEMORY_LAYOUT["framebuffer_base"] >> 12}

    li t2, 0
    li t3, {output_size}
    li t4, 0                        # col
    li t5, 0                        # row

.Lwrite_pixels:
    bge t2, t3, .Lwrite_done
    slli t6, t2, 2
    add t6, t0, t6
    flw fa0, 0(t6)
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1
    lui t6, 0x3F800
    fmv.w.x fa1, t6
    fmin.s fa0, fa0, fa1
    lui t6, 0x43800
    fmv.w.x fa1, t6
    fmul.s fa0, fa0, fa1
    fcvt.wu.s t6, fa0
    # Compute offset: row * 320 + col
    slli a5, t5, 8
    slli a6, t5, 6
    add a5, a5, a6
    add a5, a5, t4
    add a5, t1, a5
    sb t6, 0(a5)
    # Advance col/row
    addi t4, t4, 1
    li a5, 20
    bne t4, a5, .Lno_row_inc_c2c
    li t4, 0
    addi t5, t5, 1
.Lno_row_inc_c2c:
    addi t2, t2, 1
    j .Lwrite_pixels

.Lwrite_done:
    ret
"""
        else:
            return """# Output mapping: Generic - TODO
map_output_generic:
    ret
"""

    def _generate_model_forward_pass(self) -> str:
        """Generate complete forward pass through all layers."""
        if not self.layers:
            return "run_forward_pass:\n    ret\n"
        
        architecture = self.metadata.get("architecture", "")
        is_block_diagonal = "block-diagonal" in architecture
        
        if is_block_diagonal:
            # For block-diagonal, run all layers sequentially
            code = """# Forward pass (block-diagonal model)
run_forward_pass:
    addi sp, sp, -4
    sw ra, 0(sp)
"""
            for i in range(len(self.layers)):
                code += f"    call layer_{i}_forward\n"
            code += """    lw ra, 0(sp)
    addi sp, sp, 4
    ret
"""
            return code
        
        # Standard forward pass
        code = """# Forward pass through all layers
run_forward_pass:
    addi sp, sp, -4
    sw ra, 0(sp)
"""
        for i in range(len(self.layers)):
            code += f"    call layer_{i}_forward\n"
        code += """    lw ra, 0(sp)
    addi sp, sp, 4
    ret
"""
        return code

    def _generate_update_counter_state(self) -> str:
        """Generate update_counter_state for block-diagonal-parallel models."""
        return f"""# Update counter state: read counter outputs (400-654), argmax -> a0
update_counter_state:
    li t0, 0x{self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]:08X}
    li t1, 400
    li t2, 255
    li t3, 0
    li t4, 0
    add t0, t0, t1
    flw fa0, 0(t0)
.Lupdate_counter_argmax:
    bge t3, t2, .Lupdate_counter_done
    slli t5, t3, 2
    add t6, t0, t5
    flw fa1, 0(t6)
    flt.s t5, fa0, fa1
    beq t5, zero, .Lupdate_counter_next
    fsgnj.s fa0, fa1, fa1
    addi t4, t3, 0
.Lupdate_counter_next:
    addi t3, t3, 1
    j .Lupdate_counter_argmax
.Lupdate_counter_done:
    addi a0, t4, 0
    ret
"""

    def _generate_dense_layer_forward(self, layer_idx: int, layer_info: Dict,
                                      model_base: int, is_last_layer: bool = False) -> str:
        """Generate RISC-V assembly for a dense layer forward pass."""
        input_size = layer_info["input_size"]
        output_size = layer_info["output_size"]
        activation = layer_info["activation"]
        
        header_size = 28
        layer_table_size = 32 * len(self.layers)
        weights_data_start = header_size + layer_table_size
        
        weight_float_count = 0
        bias_float_count = 0
        for i in range(layer_idx):
            weight_float_count += self.layers[i]["input_size"] * self.layers[i]["output_size"]
            bias_float_count += self.layers[i]["output_size"]
        
        total_weights = sum(self.layers[j]["input_size"] * self.layers[j]["output_size"]
                           for j in range(len(self.layers)))
        weights_offset = weights_data_start + weight_float_count * 4
        biases_offset = weights_data_start + total_weights * 4 + bias_float_count * 4
        
        if layer_idx == 0:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["input"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
        elif layer_idx % 2 == 1:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_b"]
        else:
            input_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_b"]
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["activation_a"]
        
        if is_last_layer:
            output_buf = self.MEMORY_LAYOUT["buffer_base"] + self.BUFFER_OFFSETS["output"]
        
        activation_asm = ""
        if activation == "relu":
            activation_asm = """    # Apply ReLU
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1
"""
        elif activation == "sigmoid":
            activation_asm = """    # Apply Sigmoid
    call sigmoid_piecewise
"""
        
        return f"""# Layer {layer_idx}: Dense [{input_size} -> {output_size}] + {activation}
layer_{layer_idx}_forward:
    addi sp, sp, -32
    sw ra, 28(sp)
    sw s0, 24(sp)
    sw s1, 20(sp)
    sw s2, 16(sp)
    sw s3, 12(sp)
    sw s4, 8(sp)

    .option push
    .option norelax
    la s0, model_data_start
    .option pop
    lui s1, {input_buf >> 12}
    addi s1, s1, {input_buf & 0xFFF}
    lui s2, {output_buf >> 12}
    addi s2, s2, {output_buf & 0xFFF}

    li s3, 0

.L{layer_idx}_outer_loop:
    li t0, {output_size}
    bge s3, t0, .L{layer_idx}_done

    li t0, {biases_offset}
    add t1, s0, t0
    slli t2, s3, 2
    add t1, t1, t2
    flw fa0, 0(t1)

    li t5, {weights_offset}
    add t5, s0, t5
    add t5, t5, t2
    li t6, {output_size * 4}

    li s4, 0

.L{layer_idx}_inner_loop:
    li t0, {input_size}
    bge s4, t0, .L{layer_idx}_apply_activation

    slli t0, s4, 2
    add t1, s1, t0
    flw fa1, 0(t1)
    flw fa2, 0(t5)
    fmul.s fa3, fa1, fa2
    fadd.s fa0, fa0, fa3
    add t5, t5, t6
    addi s4, s4, 1
    j .L{layer_idx}_inner_loop

.L{layer_idx}_apply_activation:
{activation_asm}
    slli t0, s3, 2
    add t1, s2, t0
    fsw fa0, 0(t1)
    addi s3, s3, 1
    j .L{layer_idx}_outer_loop

.L{layer_idx}_done:
    lw ra, 28(sp)
    lw s0, 24(sp)
    lw s1, 20(sp)
    lw s2, 16(sp)
    lw s3, 12(sp)
    lw s4, 8(sp)
    addi sp, sp, 32
    ret
"""

    def _generate_sigmoid_piecewise(self) -> str:
        """Generate piecewise linear sigmoid approximation."""
        return """# Sigmoid piecewise linear approximation
sigmoid_piecewise:
    addi sp, sp, -16
    sw ra, 12(sp)
    fsw fa1, 8(sp)
    fsw fa2, 4(sp)

    lui t0, 0xC0800
    fmv.w.x fa1, t0
    fle.s t0, fa0, fa1
    beq t0, zero, .Lsig_check_high
    fmv.w.x fa0, zero
    j .Lsig_done

.Lsig_check_high:
    lui t0, 0x40800
    fmv.w.x fa1, t0
    fle.s t0, fa1, fa0
    beq t0, zero, .Lsig_linear
    lui t0, 0x3F800
    fmv.w.x fa0, t0
    j .Lsig_done

.Lsig_linear:
    lui t0, 0x3E000
    fmv.w.x fa1, t0
    fmul.s fa1, fa0, fa1
    lui t0, 0x3F000
    fmv.w.x fa2, t0
    fadd.s fa0, fa2, fa1

.Lsig_done:
    lw ra, 12(sp)
    flw fa1, 8(sp)
    flw fa2, 4(sp)
    addi sp, sp, 16
    ret
"""

    def generate_c(self, json_path: str, output_c: str, temp_bin: str = None,
                   with_execution: bool = True) -> str:
        """Generate complete C file with embedded assembly."""
        if self.verbose:
            print(f"[CModelCompiler] Generating C file: {output_c}")
        
        # Load JSON
        self.load_json_intermediate(json_path)
        
        # Generate binary format
        binary = self.generate_binary_format()
        
        # Get model info
        model_type = self.metadata.get("model_type", "unknown")
        input_size = self.layers[0]["input_size"] if self.layers else 0
        output_size = self.metadata.get("output_size", self.layers[-1]["output_size"] if self.layers else 0)
        
        # Determine model base address
        model_base = self.MEMORY_LAYOUT["generator_base"]
        
        # Build C file
        c_parts = []
        
        # Header
        c_parts.append(self._generate_c_headers(model_type))
        
        # Model data as C array
        c_parts.append(self._generate_c_model_data(binary, model_base))
        
        # Generate assembly content
        asm_code = self._generate_asm_content(model_type, input_size, output_size)
        
        # Add update_counter_state for block-diagonal-parallel
        architecture = self.metadata.get("architecture", "")
        if "block-diagonal" in architecture and architecture.endswith("-parallel"):
            asm_code += self._generate_update_counter_state()
        
        # Wrap assembly in C functions
        c_parts.append(self._generate_c_wrapped_asm(asm_code))
        
        # Add _start function that initializes stack and jumps to inference_loop
        # Note: No data copying needed since model_data is already at target address
        c_parts.append("""// Entry point
void _start(void) {
    __asm__ volatile (
        "# Initialize stack pointer to 0x20000\\n"
        "lui sp, 0x20\\n"
        "\\n"
        "# Jump directly to inference loop\\n"
        "j inference_loop"
    );
}
""")
        
        # Write C file
        c_content = '\n'.join(c_parts)
        with open(output_c, 'w') as f:
            f.write(c_content)
        
        if self.verbose:
            print(f"[CModelCompiler] Generated C file: {output_c}")
            print(f"  Size: {len(c_content)} bytes")
        
        return output_c

    def compile(self, json_path: str, output_c: str = None, with_execution: bool = True) -> Tuple[str, str]:
        """Compile JSON to C file."""
        if output_c is None:
            output_c = str(Path(json_path).with_suffix('.c'))
        
        c_path = self.generate_c(json_path, output_c, with_execution=with_execution)
        
        # Also write binary
        temp_bin = str(Path(output_c).with_suffix('.bin'))
        if self.binary_data:
            with open(temp_bin, 'wb') as f:
                f.write(self.binary_data)
        
        return c_path, temp_bin

    def compile_to_elf(self, json_path: str, output_elf: str = None, with_execution: bool = True) -> str:
        """Compile JSON to ELF file using riscv64-elf-gcc."""
        import subprocess
        
        if output_elf is None:
            output_elf = str(Path(json_path).with_suffix('.elf'))
        
        # First generate C file
        c_file = str(Path(output_elf).with_suffix('.c'))
        self.compile(json_path, c_file, with_execution=with_execution)
        
        # Compile C to ELF
        # Note: -Ttext=0 places code at address 0, but this can conflict with
        # data placement. Instead, we rely on the linker to place code and data
        # at appropriate addresses.
        cmd = [
            'riscv64-elf-gcc',
            '-march=rv32if',
            '-mabi=ilp32f',
            '-nostdlib',
            '-O1',
            '-Wl,-Ttext=0',
            '-Wl,--oformat=elf32-littleriscv',
            '-o', output_elf,
            c_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed:\n{result.stderr}")
        
        return output_elf


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Compile neural network model to C")
    parser.add_argument("json_file", help="Path to JSON intermediate format file")
    parser.add_argument("-o", "--output", default=None, help="Output C file (default: <json_file>.c)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.output is None:
        args.output = str(Path(args.json_file).with_suffix('.c'))
    
    try:
        compiler = CModelCompiler(verbose=args.verbose)
        c_path, bin_path = compiler.compile(args.json_file, args.output)
        print(f"Generated C file: {c_path}")
        print(f"Generated binary: {bin_path}")
        return 0
    except Exception as e:
        print(f"Compilation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
