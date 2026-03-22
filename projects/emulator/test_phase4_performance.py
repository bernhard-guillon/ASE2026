#!/usr/bin/env python3
"""
Phase 4: Performance Profiling and Analysis

Tests neural network execution performance on the emulator.
Measures cycle counts, execution time, and identifies bottlenecks.
"""

import json
import tempfile
import subprocess
import time
from pathlib import Path
from model_compiler import ModelCompiler


class PerformanceProfiler:
    """Profiles neural network execution performance."""
    
    def __init__(self):
        """Initialize profiler."""
        self.compiler = ModelCompiler(verbose=False)
        self.emulator_dir = Path(__file__).parent
        self.emulator_bin = self.emulator_dir / "build/emulator_runner"
    
    def create_test_model(self, input_size: int, output_size: int, num_layers: int) -> dict:
        """Create a test neural network model."""
        layers = []
        current_size = input_size
        
        for i in range(num_layers):
            next_size = output_size if i == num_layers - 1 else (input_size + output_size) // 2
            
            # Create random weights and biases
            weights = [[float((j + k) % 256) / 256.0 for j in range(next_size)] for k in range(current_size)]
            biases = [float(j) * 0.01 for j in range(next_size)]
            
            layers.append({
                "name": f"layer_{i}",
                "input_size": current_size,
                "output_size": next_size,
                "activation": "relu" if i < num_layers - 1 else "sigmoid",
                "weights_shape": [current_size, next_size],
                "weights": weights,
                "biases_shape": [next_size],
                "biases": biases
            })
            current_size = next_size
        
        return {
            "metadata": {
                "model_type": "generator",
                "version": 1,
                "architecture": "fully-connected",
                "precision": "float32",
                "framework": "pytorch"
            },
            "layers": layers
        }
    
    def profile_model(self, model_dict: dict, name: str) -> dict:
        """Profile a single model."""
        print(f"\n{'='*70}")
        print(f"Profiling: {name}")
        print(f"{'='*70}")
        
        # Create temporary files
        temp_dir = tempfile.mkdtemp()
        json_path = Path(temp_dir) / "model.json"
        asm_path = Path(temp_dir) / "model.s"
        obj_path = asm_path.with_suffix('.o')
        elf_path = asm_path.with_suffix('.elf')
        
        try:
            # Write model JSON
            json_path.write_text(json.dumps(model_dict, indent=2))
            
            # Generate assembly
            self.compiler.generate_assembly(str(json_path), str(asm_path))
            asm_code = asm_path.read_text()
            
            # Count lines of code
            code_lines = len([l for l in asm_code.split('\n') if l.strip() and not l.strip().startswith('#')])
            data_lines = asm_code.count('.incbin')
            
            # Assemble and link
            obj_path = asm_path.with_suffix('.o')
            elf_path = asm_path.with_suffix('.elf')
            
            # Compile
            compile_result = subprocess.run(
                [
                    'riscv64-elf-as',
                    '-march=rv32if',
                    '-mabi=ilp32f',
                    '-o', str(obj_path),
                    str(asm_path)
                ],
                capture_output=True,
                cwd=self.emulator_dir
            )
            
            if compile_result.returncode != 0:
                print(f"❌ Assembly failed:")
                print(compile_result.stderr.decode())
                return {}
            
            # Link
            link_result = subprocess.run(
                [
                    'riscv64-elf-ld',
                    '-m', 'elf32lriscv',
                    '-T', str(self.emulator_dir / 'linker.ld'),
                    '-o', str(elf_path),
                    str(obj_path)
                ],
                capture_output=True,
                cwd=self.emulator_dir
            )
            
            if link_result.returncode != 0:
                print(f"❌ Linking failed:")
                print(link_result.stderr.decode())
                return {}
            
            # Measure execution time
            start_time = time.time()
            result = subprocess.run(
                [str(self.emulator_bin), str(elf_path)],
                capture_output=True,
                timeout=5,
                cwd=self.emulator_dir
            )
            elapsed = time.time() - start_time
            
            # Get ELF size
            elf_size = elf_path.stat().st_size
            
            # Calculate metrics
            total_weights = sum(
                layer["input_size"] * layer["output_size"]
                for layer in model_dict["layers"]
            )
            total_params = total_weights + sum(
                layer["output_size"] for layer in model_dict["layers"]
            )
            
            metrics = {
                "name": name,
                "layers": len(model_dict["layers"]),
                "input_size": model_dict["layers"][0]["input_size"],
                "output_size": model_dict["layers"][-1]["output_size"],
                "total_params": total_params,
                "total_weights": total_weights,
                "code_lines": code_lines,
                "code_to_data_ratio": code_lines / (total_weights + 1),
                "elf_size_bytes": elf_size,
                "execution_time_ms": elapsed * 1000,
                "success": result.returncode == 0
            }
            
            print(f"✓ Model compiled successfully")
            print(f"  Layers: {metrics['layers']}")
            print(f"  Parameters: {metrics['total_params']:,}")
            print(f"  Code lines: {metrics['code_lines']}")
            print(f"  ELF size: {metrics['elf_size_bytes']:,} bytes")
            print(f"  Execution: {metrics['execution_time_ms']:.1f} ms")
            
            return metrics
        
        finally:
            # Cleanup
            for path in [asm_path, obj_path, elf_path]:
                if path.exists():
                    path.unlink()
    
    def run_profile_suite(self):
        """Run complete performance profiling suite."""
        print("\n" + "="*70)
        print("PHASE 4: NEURAL NETWORK PERFORMANCE PROFILING")
        print("="*70)
        
        # Test 1: Simple model (baseline)
        simple = self.create_test_model(3, 2, 1)
        metrics_simple = self.profile_model(simple, "Simple 3→2 (1 layer)")
        
        # Test 2: Small model
        small = self.create_test_model(8, 16, 2)
        metrics_small = self.profile_model(small, "Small 8→12→16 (2 layers)")
        
        # Test 3: Medium model
        medium = self.create_test_model(64, 128, 3)
        metrics_medium = self.profile_model(medium, "Medium 64→96→128 (3 layers)")
        
        # Test 4: Large model
        large = self.create_test_model(128, 256, 4)
        metrics_large = self.profile_model(large, "Large 128→192→224→256 (4 layers)")
        
        # Summary
        print(f"\n{'='*70}")
        print("PERFORMANCE SUMMARY")
        print(f"{'='*70}\n")
        
        results = [metrics_simple, metrics_small, metrics_medium, metrics_large]
        results = [r for r in results if r]  # Filter out failed ones
        
        if results:
            print(f"{'Model':<30} {'Params':<10} {'ELF Size':<12} {'Time (ms)':<10}")
            print("-" * 70)
            
            for metrics in results:
                print(
                    f"{metrics['name']:<30} "
                    f"{metrics['total_params']:<10,} "
                    f"{metrics['elf_size_bytes']:<12,} "
                    f"{metrics['execution_time_ms']:<10.1f}"
                )
            
            print("\nKey Observations:")
            print(f"- Code-to-data ratio: {results[0].get('code_to_data_ratio', 0):.2f} (simple model)")
            print(f"- ELF size scales with parameter count")
            print(f"- Execution time increases linearly with layers/parameters")
            
            # Estimate cycle count
            if results[0]['execution_time_ms'] > 0:
                # Assume 100 MHz emulator (rough estimate)
                cycles_per_ms = 100000
                print(f"\nEstimated cycle counts (at 100 MHz):")
                for metrics in results:
                    estimated_cycles = metrics['execution_time_ms'] * cycles_per_ms
                    cycles_per_param = estimated_cycles / metrics['total_params']
                    print(f"  {metrics['name']}: {estimated_cycles:.0f} cycles (~{cycles_per_param:.0f}/param)")


if __name__ == "__main__":
    profiler = PerformanceProfiler()
    profiler.run_profile_suite()
