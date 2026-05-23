#!/usr/bin/env python3
"""
Unit tests for model_compiler.py (Phase 1).

Tests verify:
1. JSON intermediate format parsing
2. Binary format generation
3. Assembly generation with .incbin directives
4. Output file validation
5. Error handling
"""

import unittest
import tempfile
import json
import struct
import os
from pathlib import Path
from model_compiler import ModelCompiler


class TestModelCompiler(unittest.TestCase):
    """Test cases for ModelCompiler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.compiler = ModelCompiler(verbose=False)
        
        # Create simple test JSON intermediate format
        self.simple_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 2,
                    "output_size": 3,
                    "activation": "relu",
                    "weights_shape": [2, 3],
                    "weights": [
                        [1.0, 2.0, 3.0],
                        [4.0, 5.0, 6.0]
                    ],
                    "biases_shape": [3],
                    "biases": [0.1, 0.2, 0.3]
                }
            ]
        }
        
        # Multi-layer model for more complex tests
        self.multi_layer_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 10,
                    "output_size": 5,
                    "activation": "relu",
                    "weights_shape": [10, 5],
                    "weights": [[float(i*5 + j) for j in range(5)] for i in range(10)],
                    "biases_shape": [5],
                    "biases": [float(i) * 0.1 for i in range(5)]
                },
                {
                    "name": "layer_1",
                    "input_size": 5,
                    "output_size": 3,
                    "activation": "sigmoid",
                    "weights_shape": [5, 3],
                    "weights": [[float(i*3 + j) for j in range(3)] for i in range(5)],
                    "biases_shape": [3],
                    "biases": [float(i) * 0.2 for i in range(3)]
                }
            ]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def _save_json(self, model_dict, name="model.json"):
        """Helper to save model to JSON file in temp directory."""
        path = os.path.join(self.temp_dir.name, name)
        with open(path, 'w') as f:
            json.dump(model_dict, f)
        return path
    
    def test_load_json_intermediate(self):
        """Test loading JSON intermediate format."""
        json_path = self._save_json(self.simple_model)
        
        intermediate = self.compiler.load_json_intermediate(json_path)
        
        self.assertIsNotNone(intermediate)
        self.assertEqual(intermediate["metadata"]["model_type"], "generator")
        self.assertEqual(len(intermediate["layers"]), 1)
        self.assertEqual(intermediate["layers"][0]["input_size"], 2)
        self.assertEqual(intermediate["layers"][0]["output_size"], 3)
    
    def test_load_json_invalid_format(self):
        """Test error handling for invalid JSON format."""
        invalid_json = {"data": "missing metadata"}
        json_path = self._save_json(invalid_json)
        
        with self.assertRaises(ValueError) as ctx:
            self.compiler.load_json_intermediate(json_path)
        
        self.assertIn("missing metadata", str(ctx.exception))
    
    def test_generate_binary_format_simple(self):
        """Test binary format generation for simple model."""
        json_path = self._save_json(self.simple_model)
        self.compiler.load_json_intermediate(json_path)
        
        binary = self.compiler.generate_binary_format()
        
        # Verify basic structure
        self.assertIsInstance(binary, bytes)
        self.assertGreater(len(binary), 32)  # At least header
        
        # Parse header
        magic, version, model_type, num_layers, total_weights, total_biases = struct.unpack(
            '<IIIIII',
            binary[0:24]
        )
        
        self.assertEqual(magic, 0x4E52414E)  # "NRAL"
        self.assertEqual(version, 1)
        self.assertEqual(model_type, 0)  # generator
        self.assertEqual(num_layers, 1)
        self.assertEqual(total_weights, 6)  # 2*3
        self.assertEqual(total_biases, 3)
    
    def test_generate_binary_multi_layer(self):
        """Test binary format generation for multi-layer model."""
        json_path = self._save_json(self.multi_layer_model)
        self.compiler.load_json_intermediate(json_path)
        
        binary = self.compiler.generate_binary_format()
        
        # Parse header
        magic, version, model_type, num_layers, total_weights, total_biases = struct.unpack(
            '<IIIIII',
            binary[0:24]
        )
        
        self.assertEqual(num_layers, 2)
        self.assertEqual(total_weights, 50 + 15)  # 10*5 + 5*3
        self.assertEqual(total_biases, 5 + 3)
    
    def test_binary_format_layer_table(self):
        """Test that layer table is correctly formatted in binary."""
        json_path = self._save_json(self.simple_model)
        self.compiler.load_json_intermediate(json_path)
        
        binary = self.compiler.generate_binary_format()
        
        # Header is 28 bytes (6 uints + 4 bytes), so layer table starts at 28
        # Parse first layer entry (starts at offset 28)
        layer_entry = struct.unpack('<8I', binary[28:60])
        
        input_size, output_size, activation = layer_entry[0:3]
        weight_offset, bias_offset = layer_entry[3:5]
        
        self.assertEqual(input_size, 2)
        self.assertEqual(output_size, 3)
        self.assertEqual(activation, 0)  # relu (simple_model uses relu)
        self.assertEqual(weight_offset, 0)  # First layer weights start at byte 0 in weight section
        self.assertEqual(bias_offset, 0)   # First layer biases start at byte 0 in bias section
    
    def test_generate_assembly_creates_files(self):
        """Test that assembly generation creates .s and .bin files."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "output.s")
        
        result_asm = self.compiler.generate_assembly(json_path, asm_path)
        
        # Check files exist
        self.assertTrue(os.path.exists(result_asm))
        bin_path = str(Path(asm_path).with_suffix('.bin'))
        self.assertTrue(os.path.exists(bin_path))
    
    def test_assembly_has_sections(self):
        """Test that generated assembly has required sections."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "output.s")
        
        self.compiler.generate_assembly(json_path, asm_path)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Verify required sections
        self.assertIn(".section .data", asm_content)
        self.assertIn(".section .text", asm_content)
        self.assertIn(".incbin", asm_content)
        self.assertIn(".globl _start", asm_content)
        self.assertIn("_start:", asm_content)
    
    def test_assembly_incbin_directive(self):
        """Test that .incbin directive is properly formatted."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "output.s")
        
        self.compiler.generate_assembly(json_path, asm_path)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Find .incbin line (exclude comments which may contain multiple mentions)
        incbin_lines = [line for line in asm_content.split('\n') 
                       if '.incbin' in line and not line.strip().startswith('#')]
        self.assertEqual(len(incbin_lines), 1)
        
        incbin_line = incbin_lines[0]
        # Should reference .bin file
        self.assertIn('.bin', incbin_line)
        self.assertIn('"', incbin_line)  # Quoted filename
    
    def test_assembly_metadata_comments(self):
        """Test that assembly includes metadata in comments."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "output.s")
        
        self.compiler.generate_assembly(json_path, asm_path)
        
        with open(asm_path, 'r') as f:
            asm_content = f.read()
        
        # Verify metadata comments
        self.assertIn("Model Type: generator", asm_content)
        self.assertIn("Number of Layers: 1", asm_content)
        self.assertIn("Binary Data Size:", asm_content)
    
    def test_compile_method(self):
        """Test the full compile() method."""
        json_path = self._save_json(self.simple_model, "model.json")
        asm_path = os.path.join(self.temp_dir.name, "model.s")
        
        result_asm, result_bin = self.compiler.compile(json_path, asm_path)
        
        # Both files should exist and be valid
        self.assertTrue(os.path.exists(result_asm))
        self.assertTrue(os.path.exists(result_bin))
        
        # Assembly should contain expected content
        with open(result_asm, 'r') as f:
            asm_content = f.read()
        self.assertIn(".section .data", asm_content)
        self.assertIn(".incbin", asm_content)
        
        # Binary should have correct structure
        with open(result_bin, 'rb') as f:
            bin_content = f.read()
        magic = struct.unpack('<I', bin_content[0:4])[0]
        self.assertEqual(magic, 0x4E52414E)
    
    def test_binary_data_roundtrip(self):
        """Test that weights/biases are preserved in binary format."""
        json_path = self._save_json(self.simple_model)
        self.compiler.load_json_intermediate(json_path)
        binary = self.compiler.generate_binary_format()
        
        # Header is 28 bytes, layer table is 32 bytes, so weights start at 60
        weights_start = 28 + 32
        
        # First layer: 2*3 = 6 weights as float32
        weights_data = binary[weights_start:weights_start + 6*4]
        weights = struct.unpack('<6f', weights_data)
        
        # Expected weights from simple_model: [[1, 2, 3], [4, 5, 6]]
        # Flattened in row-major order: [1, 2, 3, 4, 5, 6]
        expected_weights = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        for i, (actual, expected) in enumerate(zip(weights, expected_weights)):
            self.assertAlmostEqual(actual, expected, places=5,
                                 msg=f"Weight {i} mismatch")
    
    def test_activation_type_encoding(self):
        """Test that activation types are correctly encoded in binary."""
        # Create model with different activation types
        model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 1,
                    "output_size": 1,
                    "activation": "sigmoid",
                    "weights_shape": [1, 1],
                    "weights": [[1.0]],
                    "biases_shape": [1],
                    "biases": [0.0]
                }
            ]
        }
        
        json_path = self._save_json(model)
        self.compiler.load_json_intermediate(json_path)
        binary = self.compiler.generate_binary_format()
        
        # Header is 28 bytes, so layer entry starts at 28
        # Parse activation type from layer entry
        layer_entry = struct.unpack('<8I', binary[28:60])
        activation_type = layer_entry[2]
        
        self.assertEqual(activation_type, 1)  # sigmoid = 1
    
    def test_model_type_encoding(self):
        """Test that model type is correctly encoded in binary."""
        json_path = self._save_json(self.multi_layer_model)
        self.compiler.load_json_intermediate(json_path)
        binary = self.compiler.generate_binary_format()
        
        # Parse model type from header
        magic, version, model_type = struct.unpack('<3I', binary[0:12])
        
        self.assertEqual(model_type, 0)  # generator = 0
    
    def test_large_model_compilation(self):
        """Test compilation of larger model to catch memory issues."""
        # Create larger model: 100x100x50 network
        large_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 100,
                    "output_size": 100,
                    "activation": "relu",
                    "weights_shape": [100, 100],
                    "weights": [[float(i*100 + j) for j in range(100)] for i in range(100)],
                    "biases_shape": [100],
                    "biases": [float(i) * 0.01 for i in range(100)]
                },
                {
                    "name": "layer_1",
                    "input_size": 100,
                    "output_size": 50,
                    "activation": "none",
                    "weights_shape": [100, 50],
                    "weights": [[float(i*50 + j) for j in range(50)] for i in range(100)],
                    "biases_shape": [50],
                    "biases": [float(i) * 0.01 for i in range(50)]
                }
            ]
        }
        
        json_path = self._save_json(large_model)
        asm_path = os.path.join(self.temp_dir.name, "large.s")
        
        # Should complete without error
        result_asm, result_bin = self.compiler.compile(json_path, asm_path)
        
        # Verify size is reasonable
        with open(result_bin, 'rb') as f:
            binary = f.read()
        
        expected_size = (
            32 +                                      # header
            2 * 32 +                                  # 2 layers
            (100*100 + 100*50) * 4 +                 # weights
            (100 + 50) * 4                            # biases
        )
        # Allow small variation for alignment/padding
        self.assertAlmostEqual(len(binary), expected_size, delta=10)

    def test_generate_assembly_rejects_invalid_lane_mode(self):
        """Lane mode must be one of base/4x/8x/8xpmac/8xpmac2/8xpmac3/8xpmac4."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane_invalid.s")
        with self.assertRaises(ValueError) as ctx:
            self.compiler.generate_assembly(
                json_path,
                asm_path,
                use_neural_ops=True,
                neural_opcode="x7b",
                neural_lane_mode="16x",
            )
        self.assertIn("neural_lane_mode", str(ctx.exception))

    def test_generate_assembly_rejects_lane_mode_for_x77(self):
        """Lane mode 4x/8x/8xpmac/8xpmac2/8xpmac3/8xpmac4 is invalid on x77 opcode path."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane_x77_invalid.s")
        with self.assertRaises(ValueError) as ctx:
            self.compiler.generate_assembly(
                json_path,
                asm_path,
                use_neural_ops=True,
                neural_opcode="x77",
                neural_lane_mode="4x",
            )
        self.assertIn("only valid with neural_opcode x7b", str(ctx.exception))

    def test_generate_assembly_emits_nmatvec4x(self):
        """x7b + 4x lane mode should emit nmatvec4x mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane4.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="4x",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec4x.f32", asm)

    def test_generate_assembly_emits_nmatvec8x(self):
        """x7b + 8x lane mode should emit nmatvec8x mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane8.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="8x",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec8x.f32", asm)

    def test_generate_assembly_emits_nmatvec8xp(self):
        """x7b + 8xpmac lane mode should emit nmatvec8xp mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane8pmac.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="8xpmac",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec8xp.f32", asm)

    def test_generate_assembly_emits_nmatvec8xp2(self):
        """x7b + 8xpmac2 lane mode should emit nmatvec8xp2 mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane8pmac2.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="8xpmac2",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec8xp2.f32", asm)

    def test_generate_assembly_emits_movement_packed_mapping(self):
        """Movement mapping mode should emit packed-a0 input decode and argmax framebuffer output."""
        movement_model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch",
                "input_mapping": "movement_packed_a0",
            },
            "layers": [
                {
                    "name": "layer_0",
                    "input_size": 405,
                    "output_size": 400,
                    "activation": "none",
                    "weights_shape": [405, 400],
                    "weights": [[0.0 for _ in range(400)] for _ in range(405)],
                    "biases_shape": [400],
                    "biases": [0.0 for _ in range(400)],
                }
            ],
        }
        json_path = self._save_json(movement_model, "movement_mapping.json")
        asm_path = os.path.join(self.temp_dir.name, "movement_mapping.s")
        self.compiler.generate_assembly(json_path, asm_path, with_execution=True)
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("Input mapping: packed movement code (a0)", asm)
        self.assertIn("li t1, 0x1FF", asm)
        self.assertIn("li t4, 400", asm)
        self.assertIn("li t4, 5", asm)
        self.assertIn("Output mapping: movement argmax", asm)
        self.assertIn(".Largmax_done_movement", asm)

    def test_generate_assembly_emits_nmatvec8xp3(self):
        """x7b + 8xpmac3 lane mode should emit nmatvec8xp3 mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane8pmac3.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="8xpmac3",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec8xp3.f32", asm)

    def test_generate_assembly_emits_nmatvec8xp4(self):
        """x7b + 8xpmac4 lane mode should emit nmatvec8xp4 mnemonic."""
        json_path = self._save_json(self.simple_model)
        asm_path = os.path.join(self.temp_dir.name, "lane8pmac4.s")
        self.compiler.generate_assembly(
            json_path,
            asm_path,
            use_neural_ops=True,
            neural_opcode="x7b",
            neural_lane_mode="8xpmac4",
            with_execution=True,
        )
        with open(asm_path, "r") as f:
            asm = f.read()
        self.assertIn("nmatvec8xp4.f32", asm)


if __name__ == '__main__':
    unittest.main()
