#!/usr/bin/env python3
"""
Split C Model Compiler

Generates:
  1) <output_base>.h with embedded model weights
  2) <output_base>_runtime.c with a pure C implementation
  3) <output_base>_build.sh helper to compile to RV32 ELF

The runtime uses the same memory layout as the assembly compiler and
writes the framebuffer at 0x20000.
"""

import argparse
import json
import struct
from pathlib import Path
from typing import Dict, List
import numpy as np


MAGIC = 0x4E52414E  # "NRAL"
VERSION = 1
MODEL_TYPES = {"generator": 0, "recognizer": 1, "chained": 0}
ACTIVATIONS = {"relu": 0, "sigmoid": 1, "none": 2}

HEADER_SIZE = 28
LAYER_ENTRY_SIZE = 32


def _sanitize_symbol(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("_")
    sanitized = "".join(out)
    if not sanitized or sanitized[0].isdigit():
        sanitized = "model_" + sanitized
    return sanitized


def _sanitize_macro(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum():
            out.append(ch.upper())
        else:
            out.append("_")
    sanitized = "".join(out)
    if not sanitized or sanitized[0].isdigit():
        sanitized = "MODEL_" + sanitized
    return sanitized


def load_json(json_path: str) -> Dict:
    with open(json_path, "r") as f:
        data = json.load(f)
    if "metadata" not in data or "layers" not in data:
        raise ValueError("Invalid JSON format: missing metadata or layers")
    return data


def generate_binary(data: Dict) -> bytes:
    metadata = data["metadata"]
    layers = data["layers"]

    if metadata.get("precision") != "float32":
        raise ValueError("Only float32 precision supported")

    num_layers = len(layers)
    total_weights = sum(layer["input_size"] * layer["output_size"] for layer in layers)
    total_biases = sum(layer["output_size"] for layer in layers)

    binary = bytearray()

    header = struct.pack(
        "<IIIIII4B",
        MAGIC,
        VERSION,
        MODEL_TYPES[metadata.get("model_type")],
        num_layers,
        total_weights,
        total_biases,
        0, 0, 0, 0,
    )
    binary.extend(header)

    weight_offset = 0
    bias_offset = 0
    for layer in layers:
        activation_val = ACTIVATIONS[layer.get("activation", "none")]
        num_weights = layer["input_size"] * layer["output_size"]
        num_biases = layer["output_size"]

        entry = struct.pack(
            "<8I",
            layer["input_size"],
            layer["output_size"],
            activation_val,
            weight_offset * 4,
            bias_offset * 4,
            0, 0, 0,
        )
        binary.extend(entry)

        weight_offset += num_weights
        bias_offset += num_biases

    for layer in layers:
        weights = np.array(layer["weights"], dtype=np.float32)
        binary.extend(weights.tobytes())

    for layer in layers:
        biases = np.array(layer["biases"], dtype=np.float32)
        binary.extend(biases.tobytes())

    return bytes(binary)


def emit_header(binary: bytes, data: Dict, output_h: Path, symbol_base: str) -> None:
    macro_base = _sanitize_macro(symbol_base)
    guard = f"{macro_base}_H"

    words = len(binary) // 4
    uint32_array: List[str] = []
    for i in range(words):
        word = int.from_bytes(binary[i * 4 : (i + 1) * 4], byteorder="little", signed=False)
        uint32_array.append(f"0x{word:08X}U")

    lines = []
    for i in range(0, len(uint32_array), 8):
        line = "    " + ", ".join(uint32_array[i : i + 8])
        if i + 8 < len(uint32_array):
            line += ","
        lines.append(line)

    layers = data["layers"]
    input_size = layers[0]["input_size"] if layers else 0
    output_size = layers[-1]["output_size"] if layers else 0

    header = f"""#ifndef {guard}
#define {guard}

// Basic type definitions (no stdint.h dependency)
typedef unsigned int uint32_t;

#define {macro_base}_HEADER_SIZE {HEADER_SIZE}
#define {macro_base}_LAYER_ENTRY_SIZE {LAYER_ENTRY_SIZE}
#define {macro_base}_NUM_LAYERS {len(layers)}
#define {macro_base}_TOTAL_WEIGHTS {sum(l["input_size"] * l["output_size"] for l in layers)}
#define {macro_base}_TOTAL_BIASES {sum(l["output_size"] for l in layers)}
#define {macro_base}_INPUT_SIZE {input_size}
#define {macro_base}_OUTPUT_SIZE {output_size}
#define {macro_base}_MODEL_WORDS {words}

__attribute__((aligned(4), section(".model")))
static const uint32_t {symbol_base}_model_data[{words}] = {{
{chr(10).join(lines)}
}};

#endif /* {guard} */
"""

    output_h.write_text(header)


def emit_runtime(data: Dict, output_c: Path, header_name: str, symbol_base: str) -> None:
    macro_base = _sanitize_macro(symbol_base)

    runtime = f"""// Basic type definitions (no stdint.h dependency)
typedef unsigned int uint32_t;
typedef unsigned char uint8_t;

#include \"{header_name}\"

#define MODEL_MAGIC 0x4E52414E

#define CODE_BASE 0x00001000u
#define GENERATOR_BASE 0x00030000u
#define RECOGNIZER_BASE 0x00110000u
#define BUFFER_BASE 0x00150000u
#define FRAMEBUFFER_BASE 0x00020000u

#define INPUT_BUF (BUFFER_BASE + 0x0000u)
#define ACTIVATION_A (BUFFER_BASE + 0x1000u)
#define ACTIVATION_B (BUFFER_BASE + 0x2000u)
#define OUTPUT_BUF (BUFFER_BASE + 0x3000u)

static inline uint32_t read_a0(void) {{
    uint32_t value;
    __asm__ volatile ("mv %0, a0" : "=r"(value));
    return value;
}}

static inline float sigmoid_pwl(float x) {{
    if (x <= -4.0f) return 0.0f;
    if (x >= 4.0f) return 1.0f;
    return 0.5f + x * 0.125f;
}}

static inline void map_input_generator(void) {{
    volatile float *input = (volatile float *)INPUT_BUF;
    uint32_t code = read_a0();

    for (uint32_t i = 0; i < {macro_base}_INPUT_SIZE; i++) {{
        input[i] = 0.0f;
    }}

    if (code < {macro_base}_INPUT_SIZE) {{
        input[code] = 1.0f;
    }}
}}

static inline void map_output_generator(void) {{
    volatile float *output = (volatile float *)OUTPUT_BUF;
    volatile uint8_t *fb = (volatile uint8_t *)FRAMEBUFFER_BASE;

    for (uint32_t i = 0; i < {macro_base}_OUTPUT_SIZE; i++) {{
        float v = output[i];
        if (v < 0.0f) v = 0.0f;
        if (v > 1.0f) v = 1.0f;
        v = v * 255.0f;
        uint32_t pixel = (uint32_t)v;
        if (pixel > 255u) pixel = 255u;
        fb[i] = (uint8_t)pixel;
    }}
}}

static inline void run_forward_pass(void) {{
    const uint8_t *model_bytes = (const uint8_t *){symbol_base}_model_data;
    const uint32_t *model_u32 = (const uint32_t *){symbol_base}_model_data;

    if (model_u32[0] != MODEL_MAGIC) {{
        return;
    }}

    uint32_t num_layers = model_u32[3];
    uint32_t total_weights = model_u32[4];

    uint32_t layer_table_offset = {macro_base}_HEADER_SIZE;
    uint32_t weights_base = {macro_base}_HEADER_SIZE + num_layers * {macro_base}_LAYER_ENTRY_SIZE;
    uint32_t biases_base = weights_base + total_weights * 4u;

    volatile float *input_buf = (volatile float *)INPUT_BUF;
    volatile float *act_a = (volatile float *)ACTIVATION_A;
    volatile float *act_b = (volatile float *)ACTIVATION_B;
    volatile float *output_buf = (volatile float *)OUTPUT_BUF;

    for (uint32_t layer_idx = 0; layer_idx < num_layers; layer_idx++) {{
        const uint32_t *layer = (const uint32_t *)(model_bytes + layer_table_offset + layer_idx * {macro_base}_LAYER_ENTRY_SIZE);
        uint32_t input_size = layer[0];
        uint32_t output_size = layer[1];
        uint32_t activation = layer[2];
        uint32_t weight_offset = layer[3];
        uint32_t bias_offset = layer[4];

        const float *weights = (const float *)(model_bytes + weights_base + weight_offset);
        const float *biases = (const float *)(model_bytes + biases_base + bias_offset);

        volatile float *input_ptr;
        volatile float *output_ptr;

        if (layer_idx == 0) {{
            input_ptr = input_buf;
            output_ptr = act_a;
        }} else if (layer_idx & 1u) {{
            input_ptr = act_a;
            output_ptr = act_b;
        }} else {{
            input_ptr = act_b;
            output_ptr = act_a;
        }}

        if (layer_idx == num_layers - 1) {{
            output_ptr = output_buf;
        }}

        for (uint32_t j = 0; j < output_size; j++) {{
            float acc = biases[j];
            const float *wptr = weights + j;
            for (uint32_t i = 0; i < input_size; i++) {{
                acc += input_ptr[i] * (*wptr);
                wptr += output_size;
            }}

            if (activation == 1u) {{
                if (acc < 0.0f) acc = 0.0f;
            }} else if (activation == 2u) {{
                acc = sigmoid_pwl(acc);
            }}

            output_ptr[j] = acc;
        }}
    }}
}}

void inference_loop(void);

__attribute__((naked)) void _start(void) {{
    __asm__ volatile (
        "lui sp, 0x20\\n"
        "jal ra, inference_loop\\n"
    );
}}

void inference_loop(void) {{
    for (;;) {{
        map_input_generator();
        run_forward_pass();
        map_output_generator();
    }}
}}
"""

    output_c.write_text(runtime)


def emit_build_script(output_sh: Path, output_c: Path, output_elf: Path) -> None:
    script = f"""#!/bin/sh
set -e

RISC_V_GCC=${{RISC_V_GCC:-riscv64-elf-gcc}}

$RISC_V_GCC -march=rv32if -mabi=ilp32f -nostdlib \
  -T ../riscv_generator_high.ld -Wl,--oformat=elf32-littleriscv \
  -Wl,-e,_start -o {output_elf.name} {output_c.name} -lgcc
"""
    output_sh.write_text(script)
    output_sh.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description="Split C model compiler")
    parser.add_argument("json_file", help="Path to JSON intermediate format file")
    parser.add_argument("-o", "--output", required=True, help="Output base name (no extension)")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    output_base = Path(args.output)
    output_dir = output_base.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    symbol_base = _sanitize_symbol(output_base.stem)

    data = load_json(str(json_path))
    binary = generate_binary(data)

    header_path = output_base.with_suffix(".h")
    runtime_path = output_base.with_name(output_base.stem + "_runtime.c")
    build_path = output_base.with_name(output_base.stem + "_build.sh")
    elf_path = output_base.with_suffix(".elf")

    emit_header(binary, data, header_path, symbol_base)
    emit_runtime(data, runtime_path, header_path.name, symbol_base)
    emit_build_script(build_path, runtime_path, elf_path)

    print(f"Generated header: {header_path}")
    print(f"Generated runtime: {runtime_path}")
    print(f"Generated build script: {build_path}")
    print(f"Model bytes: {len(binary)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
