#!/usr/bin/env python3
"""
Build the 3-layer combined network with block-diagonal weight matrices.

This creates a single 3-layer network where:
- Layer 0: 255 -> 512 (counter L0 + chargen L0)
- Layer 1: 512 -> 512 (counter L1 + chargen L1)
- Layer 2: 512 -> 655 (counter L2 + chargen L2)

Each layer's weight matrix is block-diagonal with zero cross-connections.
"""

import json
import numpy as np
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    # Load the two models
    counter_path = Path("./build/counter255_three_layer.json")
    chargen_path = Path("../weight-export/character_generator.json")
    output_path = Path("./build/counter-char-combined-block-diagonal.json")
    
    if not counter_path.exists():
        print(f"ERROR: Counter model not found: {counter_path}")
        return 1
    if not chargen_path.exists():
        print(f"ERROR: Chargen model not found: {chargen_path}")
        return 1
    
    counter = load_json(counter_path)
    chargen = load_json(chargen_path)
    
    print(f"Counter model: {len(counter['layers'])} layers")
    print(f"Chargen model: {len(chargen['layers'])} layers")
    
    # Verify both have 3 layers
    assert len(counter['layers']) == 3, "Counter must have 3 layers"
    assert len(chargen['layers']) == 3, "Chargen must have 3 layers"
    
    # Build the combined model with block-diagonal layers
    combined_layers = []
    
    # Layer 0: 255 -> 512
    # Counter: 255 -> 256, Chargen: 255 -> 256
    # Combined: 255 -> 512 with block weights [W_c0 | W_g0]
    layer0_counter = counter['layers'][0]
    layer0_chargen = chargen['layers'][0]
    
    # Counter L0: 255 -> 256
    w0_counter = np.array(layer0_counter['weights'], dtype=np.float32)
    b0_counter = np.array(layer0_counter['biases'], dtype=np.float32)
    
    # Chargen L0: 255 -> 256
    w0_chargen = np.array(layer0_chargen['weights'], dtype=np.float32)
    b0_chargen = np.array(layer0_chargen['biases'], dtype=np.float32)
    
    # Block-diagonal for Layer 0: 255 -> 512
    # Since both start from same input (255), we concatenate weights horizontally
    w0_combined = np.concatenate([w0_counter, w0_chargen], axis=1)  # 255 x 512
    b0_combined = np.concatenate([b0_counter, b0_chargen])  # 512
    
    combined_layers.append({
        "name": "layer_0_parallel",
        "input_size": 255,
        "output_size": 512,
        "activation": "relu",  # Both use ReLU
        "weights_shape": [255, 512],
        "weights": w0_combined.tolist(),
        "biases_shape": [512],
        "biases": b0_combined.tolist(),
    })
    
    # Layer 1: 512 -> 512
    # Counter: 256 -> 256, Chargen: 256 -> 256
    # Combined: 512 -> 512 with block-diagonal weights
    layer1_counter = counter['layers'][1]
    layer1_chargen = chargen['layers'][1]
    
    w1_counter = np.array(layer1_counter['weights'], dtype=np.float32)  # 256 x 256
    b1_counter = np.array(layer1_counter['biases'], dtype=np.float32)  # 256
    
    w1_chargen = np.array(layer1_chargen['weights'], dtype=np.float32)  # 256 x 256
    b1_chargen = np.array(layer1_chargen['biases'], dtype=np.float32)  # 256
    
    # Block-diagonal matrix: 512 x 512
    w1_combined = np.zeros((512, 512), dtype=np.float32)
    w1_combined[:256, :256] = w1_counter  # Top-left: counter
    w1_combined[256:, 256:] = w1_chargen  # Bottom-right: chargen
    b1_combined = np.concatenate([b1_counter, b1_chargen])  # 512
    
    combined_layers.append({
        "name": "layer_1_parallel",
        "input_size": 512,
        "output_size": 512,
        "activation": "relu",
        "weights_shape": [512, 512],
        "weights": w1_combined.tolist(),
        "biases_shape": [512],
        "biases": b1_combined.tolist(),
    })
    
    # Layer 2: 512 -> 655
    # Counter: 256 -> 255, Chargen: 256 -> 400
    # Combined: 512 -> 655 with block-diagonal weights
    # 
    # IMPORTANT: Put CHARGEN first (outputs 0-399) and COUNTER second (outputs 400-654)
    # so the standard output mapping can read the first 400 values (chargen output)
    layer2_counter = counter['layers'][2]
    layer2_chargen = chargen['layers'][2]
    
    w2_counter = np.array(layer2_counter['weights'], dtype=np.float32)  # 256 x 255
    b2_counter = np.array(layer2_counter['biases'], dtype=np.float32)  # 255
    
    w2_chargen = np.array(layer2_chargen['weights'], dtype=np.float32)  # 256 x 400
    b2_chargen = np.array(layer2_chargen['biases'], dtype=np.float32)  # 400
    
    # Block-diagonal matrix: 512 x 655
    # Chargen part: reads from inputs 256-511, writes to outputs 0-399
    # Counter part: reads from inputs 0-255, writes to outputs 400-654
    w2_combined = np.zeros((512, 655), dtype=np.float32)
    w2_combined[256:, :400] = w2_chargen   # Chargen: inputs 256-511 -> outputs 0-399
    w2_combined[:256, 400:] = w2_counter   # Counter: inputs 0-255 -> outputs 400-654
    b2_combined = np.concatenate([b2_chargen, b2_counter])  # 400 + 255 = 655
    
    combined_layers.append({
        "name": "layer_2_parallel",
        "input_size": 512,
        "output_size": 655,
        "activation": "sigmoid",  # Chargen uses sigmoid, counter uses none
        "weights_shape": [512, 655],
        "weights": w2_combined.tolist(),
        "biases_shape": [655],
        "biases": b2_combined.tolist(),
    })
    
    # Build combined model JSON
    # Note: output_size is 400 (chargen only) so the standard output mapping
    # reads the first 400 values from the output buffer (which are the chargen outputs)
    combined = {
        "metadata": {
            "description": "3-layer parallel counter+chargen network with block-diagonal weights",
            "model_type": "generator",
            "version": 1,
            "architecture": "block-diagonal-parallel",
            "precision": "float32",
            "framework": "hybrid-parallel",
            "counter_layers": 3,
            "chargen_layers": 3,
            "input_size": 255,
            "output_size": 400,  # Only chargen output goes to framebuffer
            "framebuffer_size": 400,
            "internal_output_size": 655,  # Total outputs (400 chargen + 255 counter)
        },
        "input_mapping": "counter_char_a0_bridge",
        "layers": combined_layers,
        "input_size": 255,
        "output_size": 400,  # Framebuffer gets 400 values
    }
    
    save_json(combined, output_path)
    print(f"\n✓ Saved combined block-diagonal model: {output_path}")
    print(f"  Size: {output_path.stat().st_size} bytes")
    
    # Print layer summary
    print("\nCombined model layers:")
    for i, l in enumerate(combined['layers']):
        print(f"  Layer {i}: {l['name']} - {l['input_size']} -> {l['output_size']}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
