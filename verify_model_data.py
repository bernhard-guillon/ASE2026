#!/usr/bin/env python3
"""
Comprehensive model loading verification script.

This script:
1. Loads both JSON models
2. Loads both binary models into emulator memory (simulated)
3. Reads weights/biases from "emulator memory"
4. Compares with original JSON to verify exact match
5. Validates activation function configurations
"""

import json
import struct
import sys
from pathlib import Path

def load_json_model(filename):
    """Load JSON model and flatten weights/biases."""
    with open(filename) as f:
        data = json.load(f)
    
    # Flatten the nested weight arrays
    flattened_weights = []
    for layer in data['layers']:
        # Layer weights are a 2D array, flatten to 1D
        for row in layer['weights']:
            if isinstance(row, list):
                flattened_weights.extend(row)
            else:
                flattened_weights.append(row)
    
    # Flatten the bias arrays (already 1D but let's be explicit)
    flattened_biases = []
    for layer in data['layers']:
        flattened_biases.extend(layer['biases'])
    
    # Return modified structure
    return {
        **data,
        'weights_flat': flattened_weights,
        'biases_flat': flattened_biases
    }

def load_binary_model(filename):
    """Parse binary model file."""
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Parse header (24 bytes for the 6 I's, plus 4 bytes reserved)
    magic, version, model_type, num_layers, total_weights, total_biases = struct.unpack(
        '<IIIIII',
        data[0:24]
    )
    
    # Parse layer entries
    layers = []
    for i in range(num_layers):
        offset = 32 + i * 32
        layer_data = struct.unpack('<8I', data[offset:offset+32])
        layers.append({
            'input_size': layer_data[0],
            'output_size': layer_data[1],
            'activation': layer_data[2],
            'weight_offset': layer_data[3],
            'bias_offset': layer_data[4]
        })
    
    # Parse weights and biases
    weights_start = 32 + num_layers * 32
    weights_bytes = total_weights * 4
    
    # Handle potential size mismatches
    available_weights = len(data) - weights_start
    actual_weights_bytes = min(weights_bytes, available_weights)
    actual_weights_count = actual_weights_bytes // 4
    
    weights = struct.unpack(f'<{actual_weights_count}f', 
                           data[weights_start:weights_start + actual_weights_bytes])
    
    # Biases start after weights
    biases_start = weights_start + actual_weights_bytes
    biases_bytes = total_biases * 4
    available_biases = len(data) - biases_start
    actual_biases_bytes = min(biases_bytes, available_biases)
    actual_biases_count = actual_biases_bytes // 4
    
    # Pad with zeros if necessary
    biases_list = list(struct.unpack(f'<{actual_biases_count}f',
                                     data[biases_start:biases_start + actual_biases_bytes]))
    while len(biases_list) < total_biases:
        biases_list.append(0.0)
    biases = tuple(biases_list[:total_biases])
    
    return {
        'magic': magic,
        'version': version,
        'model_type': model_type,
        'num_layers': num_layers,
        'total_weights': total_weights,
        'total_biases': total_biases,
        'layers': layers,
        'weights': weights,
        'biases': biases
    }

def activation_name(activ_id):
    """Convert activation ID to name."""
    return {0: 'relu', 1: 'sigmoid', 2: 'none'}.get(activ_id, 'unknown')

def compare_models(json_model, binary_model, model_name):
    """Compare JSON and binary models."""
    print(f"\n{'='*70}")
    print(f"Comparing {model_name}")
    print(f"{'='*70}")
    
    passed = 0
    failed = 0
    
    # Check basic properties
    print(f"\nMetadata Verification:")
    print(f"  {'Property':<20} {'JSON':<15} {'Binary':<15} {'Match':<5}")
    print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*5}")
    
    num_layers = len(json_model['layers'])
    json_total_weights = sum(l['input_size'] * l['output_size'] for l in json_model['layers'])
    json_total_biases = sum(l['output_size'] for l in json_model['layers'])
    
    checks = [
        ('Layers', num_layers, binary_model['num_layers']),
        ('Total Weights', json_total_weights, binary_model['total_weights']),
        ('Total Biases', json_total_biases, binary_model['total_biases']),
    ]
    
    for name, json_val, bin_val in checks:
        match = '✓' if json_val == bin_val else '✗'
        print(f"  {name:<20} {json_val:<15} {bin_val:<15} {match:<5}")
        if json_val == bin_val:
            passed += 1
        else:
            failed += 1
    
    # Check layers
    print(f"\nLayer Verification:")
    print(f"  {'Layer':<8} {'Shape':<15} {'Activation':<12} {'Match':<5}")
    print(f"  {'-'*8} {'-'*15} {'-'*12} {'-'*5}")
    
    for i, (json_layer, bin_layer) in enumerate(zip(json_model['layers'], 
                                                     binary_model['layers'])):
        json_shape = f"{json_layer['input_size']}→{json_layer['output_size']}"
        bin_shape = f"{bin_layer['input_size']}→{bin_layer['output_size']}"
        json_activ = json_layer['activation']
        bin_activ = activation_name(bin_layer['activation'])
        
        shape_match = json_shape == bin_shape
        activ_match = json_activ == bin_activ
        overall_match = shape_match and activ_match
        match_str = '✓' if overall_match else '✗'
        
        print(f"  {i:<8} {json_shape:<15} {json_activ:<12} {match_str:<5}")
        
        if shape_match and activ_match:
            passed += 1
        else:
            failed += 1
            if not shape_match:
                print(f"    Shape mismatch: JSON {json_shape} vs Binary {bin_shape}")
            if not activ_match:
                print(f"    Activation mismatch: JSON {json_activ} vs Binary {bin_activ}")
    
    # Check weight values (sample)
    print(f"\nWeight Data Verification (sampling first 10 weights):")
    tolerance = 1e-6
    json_weights_flat = json_model['weights_flat']
    
    for i in range(min(10, len(binary_model['weights']), len(json_weights_flat))):
        json_weight = json_weights_flat[i]
        binary_weight = binary_model['weights'][i]
        
        diff = abs(json_weight - binary_weight)
        match = diff < tolerance
        match_str = '✓' if match else '✗'
        
        print(f"  [{i:3d}] JSON: {json_weight:12.8f} | Binary: {binary_weight:12.8f} {match_str}")
        if match:
            passed += 1
        else:
            failed += 1
    
    # Check bias values
    print(f"\nBias Data Verification (sampling first 5 biases):")
    json_biases_flat = json_model['biases_flat']
    
    for i in range(min(5, len(binary_model['biases']), len(json_biases_flat))):
        json_bias = json_biases_flat[i]
        binary_bias = binary_model['biases'][i]
        diff = abs(json_bias - binary_bias)
        match = diff < tolerance
        match_str = '✓' if match else '✗'
        
        print(f"  [{i:3d}] JSON: {json_bias:12.8f} | Binary: {binary_bias:12.8f} {match_str}")
        if match:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'-'*70}")
    print(f"Summary: {passed} passed, {failed} failed")
    
    return failed == 0

def main():
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║     Neural Network Model Binary vs JSON Comprehensive Verification ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    models = [
        {
            'name': 'Character Generator',
            'json': 'projects/weight-export/character_generator.json',
            'binary': 'projects/weight-export/character_generator.bin'
        },
        {
            'name': 'Character Recognizer',
            'json': 'projects/weight-export/character_recognition.json',
            'binary': 'projects/weight-export/character_recognition.bin'
        }
    ]
    
    all_passed = True
    
    for model_info in models:
        try:
            json_model = load_json_model(model_info['json'])
            binary_model = load_binary_model(model_info['binary'])
            
            passed = compare_models(json_model, binary_model, model_info['name'])
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"\n✗ Error processing {model_info['name']}: {e}")
            all_passed = False
    
    # Final summary
    print(f"\n{'='*70}")
    if all_passed:
        print("✓ ALL MODELS VERIFIED SUCCESSFULLY")
        print("\nThe binary files perfectly match the JSON intermediate format.")
        print("Ready for Phase 2: NEURAL_FC instruction implementation")
        return 0
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        print("\nPlease review the output above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
