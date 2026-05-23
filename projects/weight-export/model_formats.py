"""
Model format specifications for the weight export pipeline.

This module defines the intermediate JSON format and binary format
for neural network models that will be loaded into the RISC-V emulator.
"""

import json
import struct
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np


@dataclass
class LayerDef:
    """Definition of a single fully-connected layer."""
    name: str
    input_size: int
    output_size: int
    activation: str  # "relu", "sigmoid", "none"
    weight_offset: int  # Offset in binary file where weights start
    bias_offset: int    # Offset in binary file where biases start


@dataclass
class ModelDef:
    """Complete model definition."""
    model_type: str
    num_layers: int
    layers: List[LayerDef]
    total_weights: int  # Total number of float32 values
    total_biases: int
    total_bytes: int    # Total size of weight + bias data


class IntermediateFormat:
    """
    Intermediate JSON format for model weights.
    
    Structure:
    {
        "metadata": {
            "model_type": "generator",
            "version": 1,
            "architecture": "fully-connected",
            "precision": "float32"
        },
        "layers": [
            {
                "name": "layer_0",
                "input_size": 255,
                "output_size": 256,
                "activation": "relu",
                "weights_shape": [255, 256],
                "weights": [[w00, w01, ...], [w10, w11, ...], ...],
                "biases_shape": [256],
                "biases": [b0, b1, ..., b255]
            },
            ...
        ]
    }
    """
    
    SCHEMA_VERSION = 1
    
    @staticmethod
    def from_pytorch_model(model, model_type: str, layer_configs: List[Dict[str, Any]]) -> Dict:
        """
        Convert PyTorch model to intermediate JSON format.
        
        Args:
            model: PyTorch model instance
            model_type: str
            layer_configs: List of dicts with keys:
                - "layer_param": name of the fc layer (e.g., "fc1", "fc2")
                - "activation": "relu", "sigmoid", or "none"
        
        Returns:
            Dictionary in intermediate format
        """
        intermediate = {
            "metadata": {
                "model_type": model_type,
                "version": IntermediateFormat.SCHEMA_VERSION,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": []
        }
        
        for i, config in enumerate(layer_configs):
            layer_param = config["layer_param"]
            activation = config["activation"]
            
            # Get the layer from model
            fc_layer = getattr(model, layer_param)
            
            # Extract weights and biases
            weights = fc_layer.weight.data.cpu().numpy().astype(np.float32)
            biases = fc_layer.bias.data.cpu().numpy().astype(np.float32)
            
            # Note: PyTorch stores weights as (output_size, input_size)
            # But we want (input_size, output_size) for our layout
            weights = weights.T
            
            layer_def = {
                "name": f"layer_{i}",
                "input_size": int(weights.shape[0]),
                "output_size": int(weights.shape[1]),
                "activation": activation,
                "weights_shape": list(weights.shape),
                "weights": weights.tolist(),
                "biases_shape": list(biases.shape),
                "biases": biases.tolist()
            }
            
            intermediate["layers"].append(layer_def)
        
        return intermediate
    
    @staticmethod
    def to_json_file(intermediate: Dict, filepath: str):
        """Write intermediate format to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(intermediate, f, indent=2)
    
    @staticmethod
    def from_json_file(filepath: str) -> Dict:
        """Read intermediate format from JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)


class BinaryFormat:
    """
    Binary format for model weights (optimized for emulator loading).
    
    Memory Layout:
    [Header: 32 bytes]
        - magic: 4 bytes = 0x4E52414E ("NRAL" = Neural)
        - version: 4 bytes = 1
        - model_type: 4 bytes (0 = generator)
        - num_layers: 4 bytes
        - total_weight_floats: 4 bytes
        - total_bias_floats: 4 bytes
        - reserved[4]: 4 bytes
    
    [Layer Table: 32 bytes per layer]
        For each layer:
        - input_size: 4 bytes
        - output_size: 4 bytes
        - activation: 4 bytes (0=relu, 1=sigmoid, 2=none)
        - weight_offset: 4 bytes (offset from start of weight data)
        - bias_offset: 4 bytes (offset from start of bias data)
        - reserved[3]: 12 bytes
    
    [Weight Data: 4 bytes per float32]
        All weights packed sequentially
        Layer 0 weights, Layer 1 weights, ...
    
    [Bias Data: 4 bytes per float32]
        All biases packed sequentially
        Layer 0 biases, Layer 1 biases, ...
    """
    
    MAGIC = 0x4E52414E  # "NRAL"
    VERSION = 1
    MODEL_TYPES = {"generator": 0}
    ACTIVATIONS = {"relu": 0, "sigmoid": 1, "none": 2}
    
    HEADER_SIZE = 32
    LAYER_ENTRY_SIZE = 32
    
    @staticmethod
    def from_intermediate(intermediate: Dict) -> bytes:
        """
        Convert intermediate format to binary format.
        
        Returns:
            Byte string ready to write to file
        """
        metadata = intermediate["metadata"]
        layers = intermediate["layers"]
        
        # Validate
        if metadata["precision"] != "float32":
            raise ValueError("Only float32 precision supported")
        
        model_type_val = BinaryFormat.MODEL_TYPES[metadata["model_type"]]
        
        # Calculate offsets
        num_layers = len(layers)
        
        # Count total weights and biases
        total_weights = sum(layer["input_size"] * layer["output_size"] for layer in layers)
        total_biases = sum(layer["output_size"] for layer in layers)
        
        # Build binary data
        binary_data = bytearray()
        
        # Header (32 bytes)
        header = struct.pack(
            '<IIIIII4B',
            BinaryFormat.MAGIC,           # magic
            BinaryFormat.VERSION,         # version
            model_type_val,               # model_type
            num_layers,                   # num_layers
            total_weights,                # total_weight_floats
            total_biases,                 # total_bias_floats
            0, 0, 0, 0                    # reserved
        )
        binary_data.extend(header)
        
        # Layer table (32 bytes per layer)
        weight_offset = 0
        bias_offset = 0
        
        layer_entries = bytearray()
        for layer in layers:
            activation_val = BinaryFormat.ACTIVATIONS[layer["activation"]]
            num_weights = layer["input_size"] * layer["output_size"]
            num_biases = layer["output_size"]
            
            # 32 bytes per layer: 5 I's (20 bytes) + 3 reserved I's (12 bytes)
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
            layer_entries.extend(entry)
            
            weight_offset += num_weights
            bias_offset += num_biases
        
        binary_data.extend(layer_entries)
        
        # Weight data
        weights_data = bytearray()
        for layer in layers:
            weights = np.array(layer["weights"], dtype=np.float32)
            weights_data.extend(weights.tobytes())
        
        binary_data.extend(weights_data)
        
        # Bias data
        biases_data = bytearray()
        for layer in layers:
            biases = np.array(layer["biases"], dtype=np.float32)
            biases_data.extend(biases.tobytes())
        
        binary_data.extend(biases_data)
        
        return bytes(binary_data)
    
    @staticmethod
    def to_file(intermediate: Dict, filepath: str):
        """Write binary format to file."""
        binary_data = BinaryFormat.from_intermediate(intermediate)
        with open(filepath, 'wb') as f:
            f.write(binary_data)
    
    @staticmethod
    def from_file(filepath: str) -> Dict:
        """
        Read and parse binary format file.
        
        Returns:
            Dictionary with parsed structure
        """
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Parse header
        magic, version, model_type, num_layers, total_weights, total_biases = struct.unpack(
            '<IIIIII',
            data[0:24]
        )
        
        if magic != BinaryFormat.MAGIC:
            raise ValueError(f"Invalid magic number: {hex(magic)}")
        
        if version != BinaryFormat.VERSION:
            raise ValueError(f"Unsupported version: {version}")
        
        # Reverse lookup for model type
        model_type_name = {v: k for k, v in BinaryFormat.MODEL_TYPES.items()}[model_type]
        
        # Parse layer table
        layers = []
        for i in range(num_layers):
            offset = 32 + i * 32
            input_sz, output_sz, activ, weight_off, bias_off, _, _, _ = struct.unpack(
                '<8I',
                data[offset:offset+32]
            )
            
            activ_name = {v: k for k, v in BinaryFormat.ACTIVATIONS.items()}[activ]
            
            layers.append({
                "index": i,
                "input_size": input_sz,
                "output_size": output_sz,
                "activation": activ_name,
                "weight_offset": weight_off,
                "bias_offset": bias_off
            })
        
        # Calculate data offset
        data_offset = 32 + num_layers * 32
        
        # Parse weights and biases
        result = {
            "magic": hex(magic),
            "version": version,
            "model_type": model_type_name,
            "num_layers": num_layers,
            "total_weights": total_weights,
            "total_biases": total_biases,
            "layers": layers
        }
        
        return result
    
    @staticmethod
    def get_size_info(intermediate: Dict) -> Dict[str, int]:
        """Calculate size information for binary format."""
        layers = intermediate["layers"]
        
        total_weights = sum(layer["input_size"] * layer["output_size"] for layer in layers)
        total_biases = sum(layer["output_size"] for layer in layers)
        
        header_size = BinaryFormat.HEADER_SIZE
        layer_table_size = len(layers) * BinaryFormat.LAYER_ENTRY_SIZE
        weights_size = total_weights * 4  # float32 = 4 bytes
        biases_size = total_biases * 4
        
        total_size = header_size + layer_table_size + weights_size + biases_size
        
        return {
            "header": header_size,
            "layer_table": layer_table_size,
            "weights": weights_size,
            "biases": biases_size,
            "total": total_size
        }
