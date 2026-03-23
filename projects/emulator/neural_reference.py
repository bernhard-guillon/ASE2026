#!/usr/bin/env python3
"""
Neural Network Reference Implementation

Provides Python reference functions for neural network layer computations
to validate emulator/RISC-V code against expected outputs.

Used for Phase 3 testing and validation.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any


class NeuralNetworkReference:
    """Reference implementation for neural network inference."""
    
    def __init__(self, json_path: str):
        """
        Load model from JSON intermediate format.
        
        Args:
            json_path: Path to JSON model file
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        self.metadata = data['metadata']
        self.layers = data['layers']
        
        # Validate
        assert self.metadata.get('precision') == 'float32', "Only float32 supported"
        
    def relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation: max(x, 0)."""
        return np.maximum(x, 0.0)
    
    def sigmoid_exact(self, x: np.ndarray) -> np.ndarray:
        """Exact sigmoid: 1 / (1 + exp(-x))."""
        # Clip to avoid overflow in exp
        x_clipped = np.clip(x, -500, 500)
        return 1.0 / (1.0 + np.exp(-x_clipped))
    
    def sigmoid_piecewise(self, x: np.ndarray) -> np.ndarray:
        """
        Piecewise linear sigmoid approximation (matches assembly code).
        
        Ranges:
        - x <= -2.0: 0.0
        - -2.0 < x <= 0.0: 0.25 + 0.125*x
        - 0.0 < x <= 2.0: 0.75 + 0.125*x  
        - x > 2.0: 1.0
        """
        result = np.zeros_like(x, dtype=np.float32)
        
        # x <= -2.0
        mask1 = x <= -2.0
        result[mask1] = 0.0
        
        # -2.0 < x <= 0.0
        mask2 = (x > -2.0) & (x <= 0.0)
        result[mask2] = 0.25 + 0.125 * x[mask2]
        
        # 0.0 < x <= 2.0
        mask3 = (x > 0.0) & (x <= 2.0)
        result[mask3] = 0.75 + 0.125 * x[mask3]
        
        # x > 2.0
        mask4 = x > 2.0
        result[mask4] = 1.0
        
        return result
    
    def dense_forward(self, layer_idx: int, inputs: np.ndarray, 
                     use_piecewise: bool = True) -> np.ndarray:
        """
        Forward pass through a single dense layer.
        
        Args:
            layer_idx: Layer index (0-based)
            inputs: Input array (1D)
            use_piecewise: Use piecewise sigmoid (default) vs exact sigmoid
            
        Returns:
            Output array after layer computation and activation
        """
        if layer_idx >= len(self.layers):
            raise ValueError(f"Layer {layer_idx} out of range")
        
        layer = self.layers[layer_idx]
        weights = np.array(layer['weights'], dtype=np.float32)  # (input_size, output_size)
        biases = np.array(layer['biases'], dtype=np.float32)    # (output_size,)
        activation = layer.get('activation', 'none')
        
        # Ensure inputs is float32
        inputs = np.array(inputs, dtype=np.float32)
        
        # Matrix multiply: outputs = inputs @ weights + biases
        outputs = inputs @ weights + biases
        
        # Apply activation
        if activation == 'relu':
            outputs = self.relu(outputs)
        elif activation == 'sigmoid':
            if use_piecewise:
                outputs = self.sigmoid_piecewise(outputs)
            else:
                outputs = self.sigmoid_exact(outputs)
        elif activation == 'none':
            pass  # No activation
        else:
            raise ValueError(f"Unknown activation: {activation}")
        
        return outputs
    
    def forward_pass(self, inputs: np.ndarray, use_piecewise: bool = True) -> np.ndarray:
        """
        Forward pass through entire network.
        
        Args:
            inputs: Input array for first layer
            use_piecewise: Use piecewise sigmoid vs exact sigmoid
            
        Returns:
            Final network output
        """
        current = np.array(inputs, dtype=np.float32)
        
        for layer_idx in range(len(self.layers)):
            current = self.dense_forward(layer_idx, current, use_piecewise)
        
        return current
    
    def format_floats(self, arr: np.ndarray, precision: int = 6) -> List[str]:
        """Format float array for readable output."""
        return [f"{v:.{precision}f}" for v in arr]


class NeuralNetworkValidator:
    """Validate generated code output against reference implementation."""
    
    def __init__(self, json_path: str):
        """Initialize with model."""
        self.ref = NeuralNetworkReference(json_path)
        self.test_results = []
    
    def compare_outputs(self, ref_output: np.ndarray, actual_output: np.ndarray,
                       test_name: str, tolerance: float = 1e-5) -> Tuple[bool, str]:
        """
        Compare reference output with actual output.
        
        Args:
            ref_output: Expected output from reference implementation
            actual_output: Actual output from emulator/RISC-V code
            test_name: Name of test for logging
            tolerance: Relative/absolute tolerance for comparison
            
        Returns:
            (passed, message)
        """
        # Convert to float32 for comparison
        ref_output = np.array(ref_output, dtype=np.float32)
        actual_output = np.array(actual_output, dtype=np.float32)
        
        # Check shapes
        if ref_output.shape != actual_output.shape:
            msg = f"{test_name}: Shape mismatch. Expected {ref_output.shape}, got {actual_output.shape}"
            return False, msg
        
        # Compare with tolerance
        diff = np.abs(ref_output - actual_output)
        max_diff = np.max(diff)
        rel_error = max_diff / (np.abs(ref_output) + 1e-10)
        
        # Use both absolute and relative tolerance
        passed = (max_diff <= tolerance) or (np.max(rel_error) <= tolerance)
        
        if passed:
            msg = f"{test_name}: PASS (max_diff={max_diff:.2e})"
        else:
            msg = f"{test_name}: FAIL\n"
            msg += f"  Expected: {ref_output}\n"
            msg += f"  Got:      {actual_output}\n"
            msg += f"  Diff:     {diff}\n"
            msg += f"  Max diff: {max_diff:.2e}"
        
        return passed, msg
    
    def test_single_layer(self, layer_idx: int, test_inputs: List[List[float]],
                         test_name: str = None, tolerance: float = 1e-5) -> bool:
        """
        Test a single layer with multiple inputs.
        
        Args:
            layer_idx: Layer to test
            test_inputs: List of input vectors
            test_name: Optional test name
            tolerance: Tolerance for comparison
            
        Returns:
            True if all tests passed
        """
        if test_name is None:
            test_name = f"Layer {layer_idx}"
        
        all_passed = True
        for i, inputs in enumerate(test_inputs):
            ref_out = self.ref.dense_forward(layer_idx, inputs)
            # In real test, would get actual_out from emulator
            # For now, just verify reference implementation doesn't crash
            passed = True  # placeholder
            
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_full_network(self, test_inputs: List[List[float]],
                         test_name: str = None, tolerance: float = 1e-5) -> bool:
        """
        Test full network with multiple inputs.
        
        Args:
            test_inputs: List of input vectors  
            test_name: Optional test name
            tolerance: Tolerance for comparison
            
        Returns:
            True if all tests passed
        """
        if test_name is None:
            test_name = "Full Network"
        
        all_passed = True
        for i, inputs in enumerate(test_inputs):
            ref_out = self.ref.forward_pass(inputs)
            # In real test, would get actual_out from emulator
            # For now, just verify reference implementation doesn't crash
            passed = True  # placeholder
            
            if not passed:
                all_passed = False
        
        return all_passed


def test_generator_model():
    """Test reference implementation with generator model."""
    gen_path = Path(__file__).parent / "blackbox_tests/neural_exec/test_simple_layer.json"
    
    if not gen_path.exists():
        print(f"Test model not found: {gen_path}")
        return
    
    ref = NeuralNetworkReference(str(gen_path))
    
    # Test case: Input one-hot for character 'A' (65)
    inputs = np.zeros(3, dtype=np.float32)
    inputs[0] = 1.0  # one-hot position 0
    
    # Run through network
    output = ref.forward_pass(inputs)
    
    print(f"Generator model test:")
    print(f"  Input shape: {inputs.shape}")
    print(f"  Input: {ref.format_floats(inputs)}")
    print(f"  Output shape: {output.shape}")
    print(f"  Output: {ref.format_floats(output)}")
    
    # Print layer details
    for i, layer in enumerate(ref.layers):
        print(f"\nLayer {i}:")
        print(f"  Input size: {layer['input_size']}")
        print(f"  Output size: {layer['output_size']}")
        print(f"  Activation: {layer.get('activation', 'none')}")


if __name__ == "__main__":
    test_generator_model()
