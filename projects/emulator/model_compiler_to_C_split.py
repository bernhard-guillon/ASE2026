#!/usr/bin/env python3
"""
C Model Header Generator

Generates:
   <output_base>.h with embedded model weights + model size macros

The .h uses MODEL_ prefix and model_data symbol name.
The runtime is a separate checked-in file that includes this header.
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


def emit_header(binary: bytes, data: Dict, output_h: Path) -> None:
    guard = "MODEL_H"
    prefix = "MODEL"

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

#define {prefix}_HEADER_SIZE {HEADER_SIZE}
#define {prefix}_LAYER_ENTRY_SIZE {LAYER_ENTRY_SIZE}
#define {prefix}_NUM_LAYERS {len(layers)}
#define {prefix}_TOTAL_WEIGHTS {sum(l["input_size"] * l["output_size"] for l in layers)}
#define {prefix}_TOTAL_BIASES {sum(l["output_size"] for l in layers)}
#define {prefix}_INPUT_SIZE {input_size}
#define {prefix}_OUTPUT_SIZE {output_size}
#define {prefix}_MODEL_WORDS {words}

__attribute__((aligned(4), section(".model")))
static const uint32_t model_data[{words}] = {{
{chr(10).join(lines)}
}};

#endif /* {guard} */
"""

    output_h.write_text(header)


def main() -> int:
    parser = argparse.ArgumentParser(description="C model header generator")
    parser.add_argument("json_file", help="Path to JSON intermediate format file")
    parser.add_argument("-o", "--output", required=True, help="Output header path (no extension)")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    output_base = Path(args.output)
    output_dir = output_base.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_json(str(json_path))
    binary = generate_binary(data)

    header_path = output_base.with_suffix(".h")

    emit_header(binary, data, header_path)

    print(f"Generated header: {header_path}")
    print(f"Model bytes: {len(binary)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
