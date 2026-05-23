"""
Dataset generation for Model B (Counter Model).

Generates training data for the counter oracle using deterministic state transitions.
Each sample consists of:
- Input: encoded counter state + hit_wall bit
- Output: encoded next counter state

The dataset covers:
- All valid counter states (count 0-9, stop 0-1)
- Both hit_wall values (0 and 1)
- Edge cases: count=9 with stop=1, increment behavior, latch behavior
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from dual_model_contract import (
    CounterState,
    encode_counter_state,
    counter_step_input,
)
from counter_oracle import counter_oracle_step


def iter_all_counter_states() -> List[CounterState]:
    """
    Iterate over all valid counter states.
    
    Each state is a combination of:
    - count: 0 to 9
    - stop: 0 or 1
    
    Total: 10 * 2 = 20 states
    """
    states = []
    for count in range(10):
        for stop in [0, 1]:
            try:
                state = CounterState(count=count, stop=stop)
                states.append(state)
            except ValueError:
                pass
    return states


def generate_counter_dataset(
    npz_path: str | Path = "counter_dataset.npz",
    json_path: str | Path = "counter_transitions.json",
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate the full counter dataset.
    
    For each counter state and each hit_wall value (0, 1), compute:
    - input: encode_counter_state(state) + [hit_wall]
    - output: encode_counter_state(next_state)
    
    Args:
        npz_path: Path to save the .npz file
        json_path: Path to save the JSON metadata
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary of numpy arrays saved to npz
    """
    rng = np.random.default_rng(seed)
    
    npz_path = Path(npz_path)
    json_path = Path(json_path)
    
    # Collect all samples
    input_vectors: List[np.ndarray] = []
    output_vectors: List[np.ndarray] = []
    json_rows = []
    
    all_states = iter_all_counter_states()
    
    for state in all_states:
        for hit_wall in [0, 1]:
            # Compute oracle step
            result = counter_oracle_step(state, hit_wall)
            
            # Build input vector
            input_vec = counter_step_input(state, hit_wall)
            
            # Build output vector: next_state encoding
            next_state_enc = encode_counter_state(result.next_state)
            
            input_vectors.append(input_vec)
            output_vectors.append(next_state_enc)
            
            # JSON metadata
            json_rows.append({
                "count": state.count,
                "stop": state.stop,
                "hit_wall": hit_wall,
                "next_count": result.next_state.count,
                "next_stop": result.next_state.stop,
            })
    
    # Convert to numpy arrays
    x_data = np.asarray(input_vectors, dtype=np.float32)
    y_data = np.asarray(output_vectors, dtype=np.float32)
    
    # Expected shapes
    # input: 11 (state) + 1 (hit_wall) = 12
    # output: 11 (next_state)
    assert x_data.shape[1] == 12, f"Expected input width 12, got {x_data.shape[1]}"
    assert y_data.shape[1] == 11, f"Expected output width 11, got {y_data.shape[1]}"
    
    # Save .npz
    np.savez(
        npz_path,
        x=x_data,
        y=y_data,
        num_states=len(all_states),
        num_hit_wall_values=2,
    )
    
    # Save JSON
    json_payload = {
        "num_states": len(all_states),
        "num_samples": len(json_rows),
        "input_shape": x_data.shape[1],
        "output_shape": y_data.shape[1],
        "transitions": json_rows,
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    
    return {
        "x": x_data,
        "y": y_data,
    }


def generate_counter_trajectory_dataset(
    npz_path: str | Path = "counter_trajectory_dataset.npz",
    json_path: str | Path = "counter_trajectory_transitions.json",
    num_trajectories: int = 1000,
    steps_per_trajectory: int = 20,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate a dataset from random counter trajectories.
    
    This creates sequential data by simulating random hit_wall pulse sequences.
    Useful for testing sequence modeling.
    
    Args:
        npz_path: Path to save the .npz file
        json_path: Path to save the JSON metadata
        num_trajectories: Number of random trajectories to generate
        steps_per_trajectory: Number of steps per trajectory
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary of numpy arrays saved to npz
    """
    rng = np.random.default_rng(seed)
    
    npz_path = Path(npz_path)
    json_path = Path(json_path)
    
    input_vectors: List[np.ndarray] = []
    output_vectors: List[np.ndarray] = []
    json_rows = []
    
    trajectory_id = 0
    
    for _ in range(num_trajectories):
        # Random initial state
        count = rng.integers(0, 10)
        stop = rng.integers(0, 2)
        
        try:
            state = CounterState(count=int(count), stop=int(stop))
        except ValueError:
            continue
        
        # Random hit_wall pulses
        hit_walls = rng.integers(0, 2, size=steps_per_trajectory).tolist()
        
        # Simulate trajectory
        for step_idx, hit_wall in enumerate(hit_walls):
            result = counter_oracle_step(state, hit_wall)
            
            input_vec = counter_step_input(state, hit_wall)
            next_state_enc = encode_counter_state(result.next_state)
            
            input_vectors.append(input_vec)
            output_vectors.append(next_state_enc)
            
            json_rows.append({
                "trajectory_id": trajectory_id,
                "step": step_idx,
                "count": state.count,
                "stop": state.stop,
                "hit_wall": hit_wall,
                "next_count": result.next_state.count,
                "next_stop": result.next_state.stop,
            })
            
            state = result.next_state
        
        trajectory_id += 1
    
    x_data = np.asarray(input_vectors, dtype=np.float32)
    y_data = np.asarray(output_vectors, dtype=np.float32)
    
    np.savez(
        npz_path,
        x=x_data,
        y=y_data,
        num_trajectories=np.array([num_trajectories], dtype=np.int16),
        steps_per_trajectory=np.array([steps_per_trajectory], dtype=np.int16),
        seed=np.array([seed], dtype=np.int64),
    )
    
    json_payload = {
        "num_trajectories": num_trajectories,
        "steps_per_trajectory": steps_per_trajectory,
        "num_samples": len(json_rows),
        "input_shape": x_data.shape[1],
        "output_shape": y_data.shape[1],
        "seed": seed,
        "transitions": json_rows,
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    
    return {
        "x": x_data,
        "y": y_data,
    }


def load_counter_dataset(npz_path: str | Path = "counter_dataset.npz") -> Dict[str, np.ndarray]:
    """
    Load a counter dataset from .npz file.
    """
    payload = np.load(npz_path)
    return {k: payload[k] for k in payload.files}
