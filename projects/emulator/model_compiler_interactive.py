#!/usr/bin/env python3
"""
Interactive mode for model compiler - outputs to framebuffer with a0 looping.

This generates code that:
1. Reads character code from a0 register (set by emulator/external input)
2. Maps to one-hot input
3. Runs forward pass
4. Writes output directly to framebuffer (0x20000)
5. Loops back to step 1 (reads a0 again for next character)

This matches static_char_gen.c behavior but uses neural network.
"""

import json
from pathlib import Path
from model_compiler import ModelCompiler


class InteractiveModelCompiler(ModelCompiler):
    """Extended compiler for interactive framebuffer output."""
    
    def _generate_execution_loop_interactive(self, model_type: str) -> str:
        """Generate interactive execution loop (read a0, compute, write framebuffer, repeat)."""
        return f"""
# Interactive execution loop matching static_char_gen.c
# Reads character code from a0 each iteration, writes to framebuffer
.section .text
.align 4
.globl _start

_start:
    # Initialize stack pointer to safe location
    li sp, 0xF000              # sp = 0x0F000 (61440 bytes)
    
    # Main inference loop (infinite, like static_char_gen.c)
inference_loop:
    # Step 1: Read input character from a0 register
    # (a0 is maintained by emulator/external input each iteration)
    call map_input_{model_type}
    
    # Step 2: Run forward pass through all layers
    call run_forward_pass
    
    # Step 3: Map output directly to framebuffer (0x20000)
    call map_output_framebuffer
    
    # Step 4: Loop back to read a0 again
    j inference_loop
    
    # Unreachable, but include exit for completeness
    li a0, 0
    li a7, 93                    # SYS_exit
    ecall

"""
    
    def _generate_framebuffer_output(self) -> str:
        """Generate output mapping that writes directly to framebuffer at 0x20000 with stride-320 layout."""
        return """
# Output mapping: Network output -> Framebuffer pixels (stride-320 layout)
# Writes 400 bytes to framebuffer at 0x20000 using row*320+col addressing
map_output_framebuffer:
    # Read from output buffer at 0x00153000
    lui t0, 0x153
    addi t0, t0, 0
    lui t1, 0x20            # Framebuffer at 0x20000
    
    li t2, 0                # t2 = pixel index (0..399)
    li t3, 400              # t3 = num pixels (20x20)
    li t4, 0                # t4 = col (0..19)
    li t5, 0                # t5 = row (0..19)

.Lwrite_pixels_fb:
    bge t2, t3, .Lwrite_done_fb
    
    # Load float output[i]
    slli t6, t2, 2          # t6 = i * 4
    add t6, t0, t6          # t6 = output_buf + i*4
    flw fa0, 0(t6)          # fa0 = output[i]
    
    # Clamp to [0.0, 1.0]
    fmv.w.x fa1, zero
    fmax.s fa0, fa0, fa1    # fa0 = max(fa0, 0.0)
    lui t6, 0x3F800         # 1.0 in float
    fmv.w.x fa1, t6
    fmin.s fa0, fa0, fa1    # fa0 = min(fa0, 1.0)
    
    # Convert to byte: multiply by 255.0
    lui t6, 0x43800         # 255.0 in float
    fmv.w.x fa1, t6
    fmul.s fa0, fa0, fa1    # fa0 = fa0 * 255.0
    
    # Convert to unsigned int
    fcvt.wu.s t6, fa0       # t6 = (uint)fa0
    
    # Compute framebuffer offset: row * 320 + col
    # row * 320 = (row << 8) + (row << 6) = row*256 + row*64
    slli a5, t5, 8          # a5 = row * 256
    slli a6, t5, 6          # a6 = row * 64
    add a5, a5, a6          # a5 = row * 320
    add a5, a5, t4          # a5 = row * 320 + col
    add a5, t1, a5          # a5 = framebuf + offset
    sb t6, 0(a5)            # Store byte to framebuffer
    
    # Advance col; wrap to next row if col reaches 20
    addi t4, t4, 1
    li a5, 20
    bne t4, a5, .Lno_row_inc
    li t4, 0                # col = 0
    addi t5, t5, 1          # row++
.Lno_row_inc:
    
    addi t2, t2, 1
    j .Lwrite_pixels_fb

.Lwrite_done_fb:
    ret

"""

    def generate_assembly_interactive(self, json_path: str, output_asm: str,
                                      temp_bin: str = None,
                                      use_neural_ops: bool = False,
                                      neural_opcode: str = "x77",
                                      neural_lane_mode: str = "base") -> str:
        """
        Generate assembly for interactive framebuffer output.
        
        This modifies the standard generated code to:
        1. Read a0 each iteration (don't hardcode input)
        2. Write to framebuffer (0x20000) instead of output buffer
        3. Loop infinitely
        """
        if temp_bin is None:
            temp_bin = str(Path(output_asm).with_suffix('.bin'))
        
        # Generate the standard assembly first
        std_asm = self.generate_assembly(json_path, output_asm, temp_bin, 
                                         with_bootloader=False, with_execution=True,
                                         use_neural_ops=use_neural_ops,
                                         neural_opcode=neural_opcode,
                                         neural_lane_mode=neural_lane_mode)
        
        # Read the generated assembly
        with open(std_asm, 'r') as f:
            asm_code = f.read()
        
        # Modify 1: Remove hardcoded input character
        asm_code = asm_code.replace(
            "li a0, 65",
            "# a0 already contains character code (read by emulator)"
        )
        
        # Modify 2: REMOVED - The output buffer address should NOT be replaced
        # The code correctly reads from output buffer (0x00153000) and writes to framebuffer (0x00200000)
        # Replacing the output buffer address would cause reading from framebuffer instead!
        
        # Write modified assembly
        with open(output_asm, 'w') as f:
            f.write(asm_code)
        
        return output_asm


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Interactive Model Compiler: JSON → Interactive RISC-V Assembly"
    )
    parser.add_argument("json_file", help="Path to JSON intermediate format file")
    parser.add_argument("-o", "--output", help="Output assembly file (default: <json>.s)")
    parser.add_argument("-b", "--binary", help="Output binary file (default: <output>.bin)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--use-neural-ops",
        action="store_true",
        help="Emit custom neural op mnemonics (opcode 0x77) for layer execution",
    )
    parser.add_argument(
        "--neural-opcode",
        choices=["x77", "x7b"],
        default="x77",
        help="Custom neural opcode variant to emit when --use-neural-ops is set",
    )
    parser.add_argument(
        "--neural-lane-mode",
        choices=["base", "4x", "8x", "8xpmac", "8xpmac2", "8xpmac3", "8xpmac4"],
        default="base",
        help="For x7b neural ops: matvec variant to emit (base=nmatvecx, 4x=nmatvec4x, 8x=nmatvec8x, 8xpmac=nmatvec8xp, 8xpmac2=nmatvec8xp2, 8xpmac3=nmatvec8xp3, 8xpmac4=nmatvec8xp4)",
    )
    
    args = parser.parse_args()
    
    output_asm = args.output or f"{args.json_file}.interactive.s"
    output_bin = args.binary or f"{output_asm}.bin"
    
    compiler = InteractiveModelCompiler(verbose=args.verbose)
    result = compiler.generate_assembly_interactive(
        args.json_file,
        output_asm,
        output_bin,
        use_neural_ops=args.use_neural_ops,
        neural_opcode=args.neural_opcode,
        neural_lane_mode=args.neural_lane_mode,
    )
    
    print(f"Interactive assembly generated: {result}")
    print(f"Binary data: {output_bin}")
