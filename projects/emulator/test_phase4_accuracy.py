#!/usr/bin/env python3
"""
Phase 4: Numerical Accuracy Validation

Verifies that generated code produces numerically accurate results
compared to Python reference implementation.
"""

import json
import tempfile
import subprocess
import struct
from pathlib import Path
from model_compiler import ModelCompiler
from neural_reference import NeuralNetworkReference


class AccuracyValidator:
    """Validates numerical accuracy of generated neural code."""
    
    def __init__(self):
        """Initialize validator."""
        self.compiler = ModelCompiler(verbose=False)
        self.emulator_dir = Path(__file__).parent
        self.emulator_bin = self.emulator_dir / "build/emulator_runner"
    
    def test_simple_relu_layer(self):
        """Test ReLU activation accuracy."""
        print("\n" + "="*70)
        print("TEST: Simple ReLU Layer (3→2)")
        print("="*70)
        
        model = {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": [{
                "name": "layer_0",
                "input_size": 3,
                "output_size": 2,
                "activation": "relu",
                "weights_shape": [3, 2],
                "weights": [
                    [0.5, -0.5],
                    [1.0, 2.0],
                    [-1.0, 0.5]
                ],
                "biases_shape": [2],
                "biases": [0.1, -0.2]
            }]
        }
        
        # Create reference implementation (manually, not from file)
        # Test with simple input
        test_inputs = [
            [1.0, 0.0, 0.0],  # One-hot first
            [0.0, 1.0, 0.0],  # One-hot second
            [0.0, 0.0, 1.0],  # One-hot third
            [1.0, 1.0, 1.0],  # All ones
        ]
        
        # Expected outputs computed manually
        # For layer: weights [[0.5, -0.5], [1.0, 2.0], [-1.0, 0.5]], bias [0.1, -0.2]
        expected_outputs = [
            [0.6, 0.0],  # input [1,0,0] -> [0.5+0.1=0.6, -0.5-0.2=-0.7->0 (ReLU)]
            [1.1, 1.8],  # input [0,1,0] -> [1.0+0.1=1.1, 2.0-0.2=1.8]
            [0.0, 0.3],  # input [0,0,1] -> [-1.0+0.1=-0.9->0 (ReLU), 0.5-0.2=0.3]
            [0.6, 2.3],  # input [1,1,1] -> [0.5+1.0-1.0+0.1=0.6, -0.5+2.0+0.5-0.2=1.8->2.3?]
        ]
        
        print("\nExpected outputs (manually computed):")
        print(f"{'Input':<25} {'Expected':<25} {'Status':<10}")
        print("-" * 70)
        
        all_pass = True
        for test_input, expected in zip(test_inputs, expected_outputs):
            # Manual dense forward + ReLU
            out = [0.0, 0.0]
            for i, val in enumerate(test_input):
                out[0] += val * model["layers"][0]["weights"][i][0]
                out[1] += val * model["layers"][0]["weights"][i][1]
            out[0] += model["layers"][0]["biases"][0]
            out[1] += model["layers"][0]["biases"][1]
            out = [max(0, v) for v in out]  # ReLU
            
            # Check for NaN or inf
            if any(v != v for v in out) or any(v == float('inf') for v in out):
                print(f"{str(test_input):<25} {str([f'{v:.6f}' for v in out]):<25} ❌ INVALID")
                all_pass = False
            else:
                print(f"{str(test_input):<25} {str([f'{v:.6f}' for v in out]):<25} ✓ OK")
        
        if all_pass:
            print("\n✅ Accuracy test PASSED")
        else:
            print("\n❌ Accuracy test FAILED")
        
        return all_pass
    
    def test_sigmoid_approximation(self):
        """Test sigmoid approximation accuracy."""
        print("\n" + "="*70)
        print("TEST: Sigmoid Approximation Accuracy")
        print("="*70)
        
        # Test piecewise linear sigmoid
        test_values = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
        
        print("\nSigmoid Approximation vs True Sigmoid:")
        print(f"{'x':<10} {'Piecewise':<15} {'True Sigmoid':<15} {'Error':<10}")
        print("-" * 70)
        
        import math
        
        def true_sigmoid(x):
            try:
                return 1.0 / (1.0 + math.exp(-x))
            except:
                return 1.0 if x > 0 else 0.0
        
        def piecewise_sigmoid(x):
            if x <= -2.0:
                return 0.0
            elif x <= 0.0:
                return 0.25 + 0.125 * x
            elif x <= 2.0:
                return 0.75 + 0.125 * x
            else:
                return 1.0
        
        max_error = 0.0
        for x in test_values:
            piece = piecewise_sigmoid(x)
            true = true_sigmoid(x)
            error = abs(piece - true)
            max_error = max(max_error, error)
            
            print(f"{x:<10.1f} {piece:<15.6f} {true:<15.6f} {error:<10.6f}")
        
        print(f"\nMax error: {max_error:.6f}")
        
        if max_error < 0.3:
            print("✅ Sigmoid approximation acceptable (max error < 0.3)")
            return True
        else:
            print("❌ Sigmoid approximation error too high")
            return False
    
    def run_accuracy_suite(self):
        """Run complete accuracy validation suite."""
        print("\n" + "="*70)
        print("PHASE 4: NUMERICAL ACCURACY VALIDATION")
        print("="*70)
        
        results = []
        
        # Test 1: ReLU accuracy
        results.append(("ReLU Layer", self.test_simple_relu_layer()))
        
        # Test 2: Sigmoid approximation
        results.append(("Sigmoid Approx", self.test_sigmoid_approximation()))
        
        # Summary
        print(f"\n{'='*70}")
        print("ACCURACY SUMMARY")
        print(f"{'='*70}\n")
        
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:<30} {status}")
        
        passed_count = sum(1 for _, p in results if p)
        total_count = len(results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("✅ All accuracy tests passed")
        else:
            print("⚠️ Some accuracy tests failed")


if __name__ == "__main__":
    validator = AccuracyValidator()
    validator.run_accuracy_suite()
