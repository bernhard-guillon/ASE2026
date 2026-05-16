"""
Dataset generation for Model A (Physics Model).

Generates training data for the physics oracle using deterministic state transitions.
Each sample consists of:
- Input: encoded physics state + stop bit
- Output: encoded next physics state + hit_wall bit

The dataset covers:
- All valid physics states (ball positions x velocities)
- Both stop_bit values (0 and 1)
- Edge cases: wall collisions, corner behavior, freeze behavior
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    encode_physics_state,
    physics_step_input,
)
from physics_oracle import physics_oracle_step


# All valid velocities (Manhattan norm = 1, no diagonal)
VELOCITIES = [
    (1, 0),   # right
    (-1, 0),  # left
    (0, 1),   # down
    (0, -1),  # up
]


def iter_all_physics_states() -> List[PhysicsState]:
    """
    Iterate over all valid physics states.
    
    Each state is a combination of:
    - ball_x: 0 to GRID_SIZE-1
    - ball_y: 0 to GRID_SIZE-1
    - vel_x, vel_y: one of the 4 cardinal direction velocities
    
    Total: GRID_SIZE * GRID_SIZE * 4 = 20*20*4 = 1600 states
    """
    states = []
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            for vel_x, vel_y in VELOCITIES:
                try:
                    state = PhysicsState(
                        ball_x=x,
                        ball_y=y,
                        vel_x=vel_x,
                        vel_y=vel_y,
                    )
                    states.append(state)
                except ValueError:
                    # Shouldn't happen with our velocity list
                    pass
    return states


def generate_physics_dataset(
    npz_path: str | Path = "physics_dataset.npz",
    json_path: str | Path = "physics_transitions.json",
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate the full physics dataset.
    
    For each physics state and each stop_bit value (0, 1), compute:
    - input: encode_physics_state(state) + [stop_bit]
    - output: encode_physics_state(next_state) + [hit_wall]
    
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
    
    all_states = iter_all_physics_states()
    
    for state in all_states:
        for stop_bit in [0, 1]:
            # Compute oracle step
            result = physics_oracle_step(state, stop_bit)
            
            # Build input vector
            input_vec = physics_step_input(state, stop_bit)
            
            # Build output vector: next_state encoding + hit_wall bit
            next_state_enc = encode_physics_state(result.next_state)
            output_vec = np.concatenate([
                next_state_enc,
                np.array([result.hit_wall], dtype=np.float32),
            ])
            
            input_vectors.append(input_vec)
            output_vectors.append(output_vec)
            
            # JSON metadata
            json_rows.append({
                "ball_x": state.ball_x,
                "ball_y": state.ball_y,
                "vel_x": state.vel_x,
                "vel_y": state.vel_y,
                "stop_bit": stop_bit,
                "next_ball_x": result.next_state.ball_x,
                "next_ball_y": result.next_state.ball_y,
                "next_vel_x": result.next_state.vel_x,
                "next_vel_y": result.next_state.vel_y,
                "hit_wall": result.hit_wall,
            })
    
    # Convert to numpy arrays
    x_data = np.asarray(input_vectors, dtype=np.float32)
    y_data = np.asarray(output_vectors, dtype=np.float32)
    
    # Expected shapes
    # input: 46 (state) + 1 (stop) = 47
    # output: 46 (next_state) + 1 (hit_wall) = 47
    assert x_data.shape[1] == 47, f"Expected input width 47, got {x_data.shape[1]}"
    assert y_data.shape[1] == 47, f"Expected output width 47, got {y_data.shape[1]}"
    
    # Save .npz
    np.savez(
        npz_path,
        x=x_data,
        y=y_data,
        num_states=len(all_states),
        num_stop_values=2,
        grid_size=np.array([GRID_SIZE], dtype=np.int16),
    )
    
    # Save JSON
    json_payload = {
        "grid_size": GRID_SIZE,
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


def generate_physics_trajectory_dataset(
    npz_path: str | Path = "physics_trajectory_dataset.npz",
    json_path: str | Path = "physics_trajectory_transitions.json",
    num_trajectories: int = 1000,
    steps_per_trajectory: int = 50,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Generate a dataset from random trajectories.
    
    This is an alternative generation method that creates sequential data
    by simulating random bounces. Useful for testing sequence modeling.
    
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
    
    # Track trajectory IDs for JSON
    trajectory_id = 0
    
    for _ in range(num_trajectories):
        # Random initial state
        ball_x = rng.integers(0, GRID_SIZE)
        ball_y = rng.integers(0, GRID_SIZE)
        vel_idx = rng.integers(0, len(VELOCITIES))
        vel_x, vel_y = VELOCITIES[vel_idx]
        
        try:
            state = PhysicsState(
                ball_x=int(ball_x),
                ball_y=int(ball_y),
                vel_x=vel_x,
                vel_y=vel_y,
            )
        except ValueError:
            continue
        
        # Random stop bits (mostly 0, occasionally 1 for freeze testing)
        stop_bits = rng.integers(0, 2, size=steps_per_trajectory).tolist()
        
        # Simulate trajectory
        for step_idx, stop_bit in enumerate(stop_bits):
            result = physics_oracle_step(state, stop_bit)
            
            input_vec = physics_step_input(state, stop_bit)
            next_state_enc = encode_physics_state(result.next_state)
            output_vec = np.concatenate([
                next_state_enc,
                np.array([result.hit_wall], dtype=np.float32),
            ])
            
            input_vectors.append(input_vec)
            output_vectors.append(output_vec)
            
            json_rows.append({
                "trajectory_id": trajectory_id,
                "step": step_idx,
                "ball_x": state.ball_x,
                "ball_y": state.ball_y,
                "vel_x": state.vel_x,
                "vel_y": state.vel_y,
                "stop_bit": stop_bit,
                "next_ball_x": result.next_state.ball_x,
                "next_ball_y": result.next_state.ball_y,
                "next_vel_x": result.next_state.vel_x,
                "next_vel_y": result.next_state.vel_y,
                "hit_wall": result.hit_wall,
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
        grid_size=np.array([GRID_SIZE], dtype=np.int16),
        seed=np.array([seed], dtype=np.int64),
    )
    
    json_payload = {
        "grid_size": GRID_SIZE,
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


def load_physics_dataset(npz_path: str | Path = "physics_dataset.npz") -> Dict[str, np.ndarray]:
    """
    Load a physics dataset from .npz file.
    """
    payload = np.load(npz_path)
    return {k: payload[k] for k in payload.files}
