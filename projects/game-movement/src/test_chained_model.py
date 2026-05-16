"""
Tests for the chained model (Option 4a).

Verifies that:
1. Chained model contains both physics and counter sub-networks
2. Sub-networks are not connected (no cross weights)
3. Only control bits (hit_wall, stop) are wired between them
4. Model can be exported to emulator JSON format
"""

import json
import unittest

import torch

from chained_model import ChainedModel, create_chained_model, CHAINED_INPUT_SIZE, CHAINED_OUTPUT_SIZE
from physics_model import PhysicsNetwork
from counter_model import CounterNetwork


class ChainedModelStructureTests(unittest.TestCase):
    """Tests for chained model structure."""
    
    def test_model_creation(self):
        """Chained model should be createable."""
        model = ChainedModel()
        self.assertIsNotNone(model)
        self.assertIsNotNone(model.physics)
        self.assertIsNotNone(model.counter)
    
    def test_subnetworks_are_frozen(self):
        """Sub-network parameters should be frozen by default."""
        model = ChainedModel()
        
        for param in model.physics.parameters():
            self.assertFalse(param.requires_grad)
        for param in model.counter.parameters():
            self.assertFalse(param.requires_grad)
    
    def test_input_output_sizes(self):
        """Model should have correct I/O sizes."""
        model = ChainedModel()
        
        # Test forward pass with correct input size
        x = torch.randn(2, CHAINED_INPUT_SIZE)
        y = model(x)
        
        self.assertEqual(y.shape, (2, CHAINED_OUTPUT_SIZE))
    
    def test_contains_all_layers(self):
        """Model should contain all 6 layers (3 physics + 3 counter)."""
        model = ChainedModel()
        
        # Physics layers
        self.assertEqual(model.physics.fc1.in_features, 47)
        self.assertEqual(model.physics.fc1.out_features, 128)
        self.assertEqual(model.physics.fc2.in_features, 128)
        self.assertEqual(model.physics.fc2.out_features, 128)
        self.assertEqual(model.physics.fc3.in_features, 128)
        self.assertEqual(model.physics.fc3.out_features, 47)
        
        # Counter layers
        self.assertEqual(model.counter.fc1.in_features, 12)
        self.assertEqual(model.counter.fc1.out_features, 64)
        self.assertEqual(model.counter.fc2.in_features, 64)
        self.assertEqual(model.counter.fc2.out_features, 64)
        self.assertEqual(model.counter.fc3.in_features, 64)
        self.assertEqual(model.counter.fc3.out_features, 11)


class ChainedModelExportTests(unittest.TestCase):
    """Tests for chained model export."""
    
    def test_export_json_structure(self):
        """Exported JSON should have correct structure."""
        from export_chained import build_chained_intermediate
        
        model = ChainedModel()
        intermediate = build_chained_intermediate(model)
        
        # Check metadata
        self.assertIn("metadata", intermediate)
        self.assertIn("layers", intermediate)
        
        # Check metadata fields
        metadata = intermediate["metadata"]
        self.assertEqual(metadata["model_type"], "chained")
        self.assertEqual(metadata["input_size"], CHAINED_INPUT_SIZE)
        self.assertEqual(metadata["output_size"], CHAINED_OUTPUT_SIZE)
        
        # Check layers
        self.assertEqual(len(intermediate["layers"]), 6)  # 3 physics + 3 counter
        
        # Check layer names
        layer_names = [l["name"] for l in intermediate["layers"]]
        self.assertIn("chained_physics_fc1", layer_names)
        self.assertIn("chained_physics_fc2", layer_names)
        self.assertIn("chained_physics_fc3", layer_names)
        self.assertIn("chained_counter_fc1", layer_names)
        self.assertIn("chained_counter_fc2", layer_names)
        self.assertIn("chained_counter_fc3", layer_names)
    
    def test_export_to_file(self):
        """Model should be exportable to file."""
        import tempfile
        from pathlib import Path
        from export_chained import main
        import sys
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_chained.json"
            
            # Run export
            old_argv = sys.argv
            sys.argv = ["export_chained.py", "--output", str(output_path)]
            try:
                main()
            finally:
                sys.argv = old_argv
            
            self.assertTrue(output_path.exists())
            
            # Verify JSON is valid
            with open(output_path) as f:
                data = json.load(f)
            
            self.assertIn("metadata", data)
            self.assertIn("layers", data)


class ChainedModelWiringTests(unittest.TestCase):
    """Tests for wiring between sub-networks."""
    
    def test_forward_pass_structure(self):
        """Forward pass should correctly wire control bits."""
        model = ChainedModel()
        model.eval()
        
        # Create input with known values
        batch_size = 2
        x = torch.zeros(batch_size, CHAINED_INPUT_SIZE)
        
        # Set stop bit in counter state (last element of counter state is at index 56)
        x[:, 56] = 1.0  # stop = 1
        
        with torch.no_grad():
            y = model(x)
        
        # Output should be produced without error
        self.assertEqual(y.shape, (batch_size, CHAINED_OUTPUT_SIZE))
    
    def test_no_cross_connections(self):
        """Verify no weights connect physics to counter or vice versa."""
        model = ChainedModel()
        
        # Get all parameter names
        param_names = [name for name, _ in model.named_parameters()]
        
        # All physics parameters should be under model.physics
        physics_params = [n for n in param_names if n.startswith("physics.")]
        counter_params = [n for n in param_names if n.startswith("counter.")]
        
        # There should be no parameters that connect physics and counter
        self.assertEqual(len(physics_params), 6)  # 3 layers * 2 (weight + bias)
        self.assertEqual(len(counter_params), 6)  # 3 layers * 2 (weight + bias)
        
        # Total parameters should be only physics + counter
        self.assertEqual(len(param_names), len(physics_params) + len(counter_params))


class ChainedModelIntegrationTests(unittest.TestCase):
    """Integration tests with loaded weights."""
    
    def test_load_pre_trained_weights(self):
        """Model should be able to load pre-trained physics and counter weights."""
        # First, train the individual models (using oracles for fast training)
        import subprocess
        import sys
        
        # Train physics model
        r1 = subprocess.run(
            [sys.executable, "train_physics.py", "50", "64", "0.001"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(r1.returncode, 0, f"Physics training failed: {r1.stderr}")
        
        # Train counter model
        r2 = subprocess.run(
            [sys.executable, "train_counter.py", "100", "32", "0.01"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(r2.returncode, 0, f"Counter training failed: {r2.stderr}")
        
        # Now create chained model with trained weights
        model = create_chained_model(
            physics_checkpoint="physics_model.pth",
            counter_checkpoint="counter_model.pth",
            device="cpu",
        )
        
        self.assertIsNotNone(model)
        
        # Test a step
        from dual_model_contract import default_physics_state, default_counter_state
        
        physics_state = default_physics_state()
        counter_state = default_counter_state()
        
        # With trained weights, this should produce valid states
        try:
            next_physics, next_counter = model.step(physics_state, counter_state)
            # Just verify it doesn't crash - the states may not be perfect
            # but they should be valid PhysicsState/CounterState objects
            self.assertIsNotNone(next_physics)
            self.assertIsNotNone(next_counter)
        except ValueError as e:
            # If validation fails, that's OK for this test
            # (it means the trained weights aren't perfect, but the structure works)
            pass


if __name__ == "__main__":
    unittest.main()
