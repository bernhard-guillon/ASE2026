#!/usr/bin/env python3
"""
Blackbox tests for parallel counter-chargen network comparison.

Tests that both standalone networks and the combined network produce
consistent outputs for characters a-g.

Phase 1: Capture reference outputs from neural.elf (standalone chargen)
Phase 2: Test counter-char.elf (3-layer chargen, known working)
Phase 3: Test counter-char-combined.elf (current 4-layer sequential)
Phase 4: Compare all outputs
"""

import subprocess
import re
import os
import json
from pathlib import Path

EMULATOR_DIR = Path(__file__).resolve().parents[1]
EMULATOR_RUNNER = EMULATOR_DIR / "build" / "emulator_runner"
NEURAL_ELF = EMULATOR_DIR / "neural.elf"
COUNTER_CHAR_ELF = EMULATOR_DIR / "build" / "counter-char.elf"
COUNTER_CHAR_COMBINED_ELF = EMULATOR_DIR / "build" / "counter-char-combined.elf"
COUNTER_CHAR_BLOCK_DIAGONAL_ELF = EMULATOR_DIR / "build" / "counter-char-combined-block-diagonal.elf"

# Characters to test
TEST_CHARS = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
ASCII_VALUES = {c: ord(c) for c in TEST_CHARS}
CYCLES = 20000000

# Output directory
OUTPUT_DIR = EMULATOR_DIR / "blackbox_tests" / "reference_outputs"


def run_emulator(elf_path, char_input, cycles=CYCLES, dump_framebuffer=True):
    """Run emulator and return framebuffer hex string."""
    cmd = [
        str(EMULATOR_RUNNER),
        str(elf_path),
        "--char", char_input,
        "--cycles", str(cycles),
    ]
    if dump_framebuffer:
        cmd.append("--dump-framebuffer")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=EMULATOR_DIR)
    
    # Extract FRAMEBUFFER_HEX line from stdout or stderr
    for line in (result.stdout + result.stderr).split('\n'):
        if line.startswith('FRAMEBUFFER_HEX:'):
            return line.split(':', 1)[1].strip()
    
    return None


def hex_to_bytes(hex_str):
    """Convert hex string to bytes."""
    if hex_str is None:
        return None
    return bytes.fromhex(hex_str)


def bytes_to_grid(bytes_data):
    """Convert framebuffer bytes to 20x20 grid of pixel values."""
    if bytes_data is None:
        return None
    grid = []
    for row in range(20):
        grid.append(list(bytes_data[row*20:(row+1)*20]))
    return grid


def compare_framebuffers(ref_hex, test_hex, threshold=127):
    """
    Compare two framebuffer hex strings using >127 threshold.
    Returns (match, diff_count, diff_details)
    """
    ref_bytes = hex_to_bytes(ref_hex)
    test_bytes = hex_to_bytes(test_hex)
    
    if ref_bytes is None or test_bytes is None:
        return False, -1, "Missing data"
    
    if len(ref_bytes) != len(test_bytes):
        return False, -1, f"Length mismatch: {len(ref_bytes)} vs {len(test_bytes)}"
    
    # Compare using >127 threshold (binary comparison)
    diffs = []
    for i in range(len(ref_bytes)):
        ref_on = ref_bytes[i] > threshold
        test_on = test_bytes[i] > threshold
        if ref_on != test_on:
            row = i // 20
            col = i % 20
            diffs.append((row, col, ref_bytes[i], test_bytes[i]))
    
    return len(diffs) == 0, len(diffs), diffs[:10]  # Return first 10 diffs


def save_reference(char, hex_str, output_dir):
    """Save reference output for a character."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"neural_{char}.txt"
    with open(output_file, 'w') as f:
        f.write(f"CHAR:{char}\n")
        f.write(f"ASCII:{ord(char)}\n")
        f.write(f"HEX:{hex_str}\n")
    return output_file


def load_reference(char, output_dir):
    """Load reference output for a character."""
    output_file = output_dir / f"neural_{char}.txt"
    if not output_file.exists():
        return None
    with open(output_file, 'r') as f:
        for line in f:
            if line.startswith("HEX:"):
                return line[4:].strip()
    return None


def test_network(name, elf_path, chars, save_refs=False):
    """Test a network and return results."""
    print(f"\nTesting {name}:")
    print("-" * 50)
    
    results = {}
    for char in chars:
        hex_output = run_emulator(elf_path, char)
        if hex_output:
            results[char] = hex_output
            if save_refs:
                save_reference(char, hex_output, OUTPUT_DIR)
                print(f"  '{char}': captured & saved")
            else:
                print(f"  '{char}': captured")
        else:
            print(f"  '{char}': FAILED")
            results[char] = None
    
    return results


def compare_networks(ref_name, ref_results, test_name, test_results, threshold=127):
    """Compare two networks' outputs."""
    print(f"\n{test_name} vs {ref_name}:")
    print("-" * 50)
    
    all_pass = True
    total_diffs = 0
    
    for char in TEST_CHARS:
        ref_hex = ref_results.get(char)
        test_hex = test_results.get(char)
        
        if ref_hex is None or test_hex is None:
            print(f"  '{char}': SKIP (missing data)")
            continue
        
        match, diff_count, diffs = compare_framebuffers(ref_hex, test_hex, threshold)
        total_diffs += diff_count
        
        if match:
            print(f"  '{char}': ✓ PASS (exact match)")
        else:
            print(f"  '{char}': ✗ FAIL ({diff_count} differing pixels)")
            if diff_count <= 10:
                for row, col, ref_val, test_val in diffs:
                    print(f"      Row {row}, Col {col}: ref={ref_val}, test={test_val}")
            all_pass = False
    
    print(f"  Total diffs across all chars: {total_diffs}")
    return all_pass


def main():
    print("="*60)
    print("Blackbox Tests: Parallel Network Comparison")
    print("Characters:", " ".join(TEST_CHARS))
    print("="*60)
    
    # Phase 1: Capture references from neural.elf
    print("\n[PHASE 1] Capturing references from neural.elf...")
    neural_results = test_network("neural.elf (standalone chargen)", 
                                   NEURAL_ELF, TEST_CHARS, save_refs=True)
    
    if not all(v is not None for v in neural_results.values()):
        print("\n❌ ERROR: Failed to capture some references")
        return 1
    
    # Phase 2: Test counter-char.elf
    print("\n[PHASE 2] Testing counter-char.elf...")
    counter_char_results = test_network("counter-char.elf", 
                                          COUNTER_CHAR_ELF, TEST_CHARS)
    
    # Phase 3: Test counter-char-combined.elf (old 4-layer)
    print("\n[PHASE 3] Testing counter-char-combined.elf (old 4-layer)...")
    combined_old_results = test_network("counter-char-combined.elf (old)", 
                                         COUNTER_CHAR_COMBINED_ELF, TEST_CHARS)
    
    # Phase 4: Test block-diagonal combined.elf (new 3-layer parallel)
    print("\n[PHASE 4] Testing counter-char-combined-block-diagonal.elf (3-layer parallel)...")
    combined_bd_results = test_network("counter-char-combined-block-diagonal.elf", 
                                        COUNTER_CHAR_BLOCK_DIAGONAL_ELF, TEST_CHARS)
    
    # Phase 5: Comparisons
    print("\n[PHASE 5] Comparisons:")
    
    # Counter-char vs Neural (should match - known working)
    counter_char_pass = compare_networks(
        "neural.elf", neural_results,
        "counter-char.elf", counter_char_results
    )
    
    # Old Combined vs Neural (expected to fail)
    combined_old_pass = compare_networks(
        "neural.elf", neural_results,
        "counter-char-combined.elf (old)", combined_old_results
    )
    
    # Block-Diagonal Combined vs Neural (should match!)
    combined_bd_pass = compare_networks(
        "neural.elf", neural_results,
        "counter-char-combined-block-diagonal.elf", combined_bd_results
    )
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Counter-Char (3-layer chargen): {'✓ ALL PASS' if counter_char_pass else '✗ SOME FAIL'}")
    print(f"Counter-Char-Combined (old 4-layer): {'✓ ALL PASS' if combined_old_pass else '✗ SOME FAIL'}")
    print(f"Counter-Char-Block-Diagonal (3-layer parallel): {'✓ ALL PASS' if combined_bd_pass else '✗ SOME FAIL'}")
    
    print("\nReference outputs saved to:", OUTPUT_DIR)
    
    if counter_char_pass and not combined_old_pass and not combined_bd_pass:
        print("\n✓ Counter-char matches neural (baseline working)")
        print("✗ Old Combined does NOT match neural")
        print("✗ Block-Diagonal Combined does NOT match neural")
        return 1
    elif counter_char_pass and not combined_old_pass and combined_bd_pass:
        print("\n✓ Counter-char matches neural (baseline working)")
        print("✗ Old Combined does NOT match neural (expected)")
        print("✓ Block-Diagonal Combined MATCHES neural!")
        return 0
    elif counter_char_pass and combined_old_pass and combined_bd_pass:
        print("\n✓ ALL TESTS PASS!")
        return 0
    else:
        print("\n❌ Unexpected results")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
