#!/usr/bin/env python3
"""
Export character recognition model to intermediate and binary formats.

Pipeline:
1. Load trained PyTorch model
2. Export to intermediate JSON format (human-readable, debuggable)
3. Convert to binary format (optimized for C loading)
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "character-recognition" / "src"))

import torch
from model_formats import IntermediateFormat, BinaryFormat
from model import CharacterNetwork


def main():
    # Paths
    project_root = Path(__file__).parent.parent
    recog_model_path = project_root / "character-recognition" / "src" / "model.pth"
    weight_export_dir = Path(__file__).parent
    
    intermediate_json = weight_export_dir / "character_recognition.json"
    binary_file = weight_export_dir / "character_recognition.bin"
    
    print("=" * 60)
    print("Character Recognition Weight Export Pipeline")
    print("=" * 60)
    
    # Check if model exists
    if not recog_model_path.exists():
        print(f"❌ Model not found: {recog_model_path}")
        print("   Please train the character recognition model first.")
        return False
    
    print(f"\n📦 Loading model from: {recog_model_path}")
    
    # Load model
    model = CharacterNetwork(input_size=400, hidden_size=128, output_size=37)
    checkpoint = torch.load(recog_model_path, map_location='cpu')
    
    # Handle both state_dict and full model checkpoints
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.eval()
    print("✓ Model loaded successfully")
    
    # Layer configuration for recognizer
    layer_configs = [
        {"layer_param": "fc1", "activation": "relu"},
        {"layer_param": "fc2", "activation": "none"}
    ]
    
    # Stage 1: Convert to intermediate JSON format
    print(f"\n🔄 Stage 1: PyTorch → Intermediate JSON")
    intermediate = IntermediateFormat.from_pytorch_model(
        model, 
        "recognizer",
        layer_configs
    )
    
    # Calculate sizes
    size_info = BinaryFormat.get_size_info(intermediate)
    
    print(f"   Layers: {len(intermediate['layers'])}")
    for i, layer in enumerate(intermediate['layers']):
        params = layer["input_size"] * layer["output_size"] + layer["output_size"]
        print(f"   - Layer {i}: {layer['input_size']}→{layer['output_size']} + {layer['activation']}")
        print(f"     Parameters: {params:,}")
    
    print(f"\n   Total weights: {size_info['weights']:,} bytes")
    print(f"   Total biases: {size_info['biases']:,} bytes")
    print(f"   Total data: {size_info['total']:,} bytes")
    
    # Save intermediate format
    print(f"\n💾 Saving intermediate JSON: {intermediate_json}")
    IntermediateFormat.to_json_file(intermediate, str(intermediate_json))
    print(f"   ✓ {intermediate_json.stat().st_size:,} bytes")
    
    # Stage 2: Convert to binary format
    print(f"\n🔄 Stage 2: Intermediate JSON → Binary Format")
    BinaryFormat.to_file(intermediate, str(binary_file))
    print(f"   ✓ {binary_file.stat().st_size:,} bytes")
    
    print("\n" + "=" * 60)
    print("✓ Character Recognition Export Complete!")
    print("=" * 60)
    print(f"\nDeliverables:")
    print(f"  • {intermediate_json} (1.8 MB) - Human-readable intermediate format")
    print(f"  • {binary_file} (0.2 MB) - Binary format for C loading")
    print(f"\nUsage:")
    print(f"  - JSON: Load in Python, inspect, validate")
    print(f"  - Binary: Load in C emulator for inference")
    print(f"\nNext: Use binary files to load into emulator")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
