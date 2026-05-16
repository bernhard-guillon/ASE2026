"""
Chain Integrator for Two-Model Squash Control Chain.

Implements the closed-loop integration of Model A (Physics) and Model B (Counter):

Tick order:
1. Run Model A with (physics_state, stop_bit) -> (next_physics_state, hit_wall)
2. Run Model B with (counter_state, hit_wall) -> (next_counter_state, stop_bit)
3. Feed stop_bit into next Model A tick

This module provides both:
- Pure-oracle integration (for deterministic baseline)
- ML-model integration (once models are trained)
- Integration with deterministic renderer for visualization
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import torch

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    CounterState,
    default_physics_state,
    default_counter_state,
    encode_physics_state,
    encode_counter_state,
)
from physics_oracle import physics_oracle_step, simulate_physics_trajectory
from counter_oracle import counter_oracle_step, simulate_counter_trajectory
from deterministic_renderer import render_frame, render_frame_compact


@dataclass
class ChainState:
    """Complete state of the dual-model chain at a single tick."""
    physics_state: PhysicsState
    counter_state: CounterState
    hit_wall: int = 0
    stop: int = 0


@dataclass
class ChainStepResult:
    """Result of a single chain integration step."""
    next_chain_state: ChainState
    frame: str  # Rendered frame (20x20 with newlines)
    frame_compact: str  # Rendered frame (400 chars, no newlines)


@dataclass
class ChainSimulationResult:
    """Result of a full chain simulation."""
    states: List[ChainState]
    frames: List[str]
    frames_compact: List[str]
    hit_wall_history: List[int]
    stop_history: List[int]
    final_physics_state: PhysicsState
    final_counter_state: CounterState
    num_ticks: int
    stop_reached: bool
    freeze_tick: Optional[int]  # Tick when stop was first asserted


def oracle_physics_fn(state: PhysicsState, stop_bit: int) -> Tuple[PhysicsState, int]:
    """Oracle physics function for chain integration."""
    result = physics_oracle_step(state, stop_bit)
    return result.next_state, result.hit_wall


def oracle_counter_fn(state: CounterState, hit_wall: int) -> CounterState:
    """Oracle counter function for chain integration."""
    result = counter_oracle_step(state, hit_wall)
    return result.next_state


def ml_physics_fn(
    model: torch.nn.Module,
    state: PhysicsState,
    stop_bit: int,
    device: str = "cpu",
) -> Tuple[PhysicsState, int]:
    """
    ML-based physics function for chain integration.
    
    Uses a trained model to predict the next physics state.
    """
    from physics_model import PHYSICS_INPUT_SIZE, PHYSICS_OUTPUT_SIZE
    from dual_model_contract import decode_physics_state, physics_step_input
    
    model.eval()
    with torch.no_grad():
        # Encode state and stop bit
        input_vec = physics_step_input(state, stop_bit)
        input_tensor = torch.tensor(input_vec, dtype=torch.float32, device=device).unsqueeze(0)
        
        # Predict
        output_tensor = model(input_tensor)
        output_vec = output_tensor.squeeze().cpu().numpy()
    
    # Decode next state (first 46 elements)
    next_state_enc = output_vec[:46]
    next_state = decode_physics_state(next_state_enc)
    
    # Get hit_wall (last element, sigmoid to get 0/1)
    hit_wall_logit = output_vec[46]
    hit_wall = 1 if hit_wall_logit > 0 else 0
    
    return next_state, hit_wall


def ml_counter_fn(
    model: torch.nn.Module,
    state: CounterState,
    hit_wall: int,
    device: str = "cpu",
) -> CounterState:
    """
    ML-based counter function for chain integration.
    
    Uses a trained model to predict the next counter state.
    """
    from counter_model import COUNTER_INPUT_SIZE, COUNTER_OUTPUT_SIZE
    from dual_model_contract import decode_counter_state, counter_step_input
    
    model.eval()
    with torch.no_grad():
        # Encode state and hit_wall
        input_vec = counter_step_input(state, hit_wall)
        input_tensor = torch.tensor(input_vec, dtype=torch.float32, device=device).unsqueeze(0)
        
        # Predict
        output_tensor = model(input_tensor)
        output_vec = output_tensor.squeeze().cpu().numpy()
    
    # Decode next state
    next_state = decode_counter_state(output_vec)
    
    return next_state


def chain_step(
    physics_state: PhysicsState,
    counter_state: CounterState,
    physics_fn: Callable[[PhysicsState, int], Tuple[PhysicsState, int]] = oracle_physics_fn,
    counter_fn: Callable[[CounterState, int], CounterState] = oracle_counter_fn,
) -> ChainStepResult:
    """
    Perform a single chain integration step.
    
    Args:
        physics_state: Current physics state
        counter_state: Current counter state
        physics_fn: Function to compute physics step (oracle or ML)
        counter_fn: Function to compute counter step (oracle or ML)
    
    Returns:
        ChainStepResult with next states and rendered frames
    """
    # Step 1: Physics step
    next_physics, hit_wall = physics_fn(physics_state, counter_state.stop)
    
    # Step 2: Counter step
    next_counter = counter_fn(counter_state, hit_wall)
    
    # Create chain state
    next_chain = ChainState(
        physics_state=next_physics,
        counter_state=next_counter,
        hit_wall=hit_wall,
        stop=next_counter.stop,
    )
    
    # Render frames
    frame = render_frame(next_physics, next_counter)
    frame_compact = render_frame_compact(next_physics, next_counter)
    
    return ChainStepResult(
        next_chain_state=next_chain,
        frame=frame,
        frame_compact=frame_compact,
    )


def simulate_chain(
    initial_physics: PhysicsState = None,
    initial_counter: CounterState = None,
    max_ticks: int = 500,
    physics_fn: Callable = oracle_physics_fn,
    counter_fn: Callable = oracle_counter_fn,
    stop_at_freeze: bool = True,
) -> ChainSimulationResult:
    """
    Simulate the full dual-model chain.
    
    Args:
        initial_physics: Starting physics state (default: (1, 1) moving right)
        initial_counter: Starting counter state (default: count=0, stop=0)
        max_ticks: Maximum number of ticks to simulate
        physics_fn: Function to compute physics step
        counter_fn: Function to compute counter step
        stop_at_freeze: If True, stop simulation when stop_bit becomes 1
    
    Returns:
        ChainSimulationResult with full history
    """
    if initial_physics is None:
        initial_physics = default_physics_state()
    if initial_counter is None:
        initial_counter = default_counter_state()
    
    states: List[ChainState] = []
    frames: List[str] = []
    frames_compact: List[str] = []
    hit_wall_history: List[int] = []
    stop_history: List[int] = []
    
    current_physics = initial_physics
    current_counter = initial_counter
    freeze_tick = None
    
    # Initial state
    initial_chain = ChainState(
        physics_state=current_physics,
        counter_state=current_counter,
        hit_wall=0,
        stop=current_counter.stop,
    )
    states.append(initial_chain)
    frames.append(render_frame(current_physics, current_counter))
    frames_compact.append(render_frame_compact(current_physics, current_counter))
    stop_history.append(current_counter.stop)
    
    for tick in range(1, max_ticks + 1):
        result = chain_step(
            current_physics,
            current_counter,
            physics_fn=physics_fn,
            counter_fn=counter_fn,
        )
        
        next_chain = result.next_chain_state
        current_physics = next_chain.physics_state
        current_counter = next_chain.counter_state
        
        states.append(next_chain)
        frames.append(result.frame)
        frames_compact.append(result.frame_compact)
        hit_wall_history.append(next_chain.hit_wall)
        stop_history.append(next_chain.stop)
        
        # Track when stop was first asserted
        if next_chain.stop == 1 and freeze_tick is None:
            freeze_tick = tick
        
        # Stop early if ball is frozen and we want to stop
        if stop_at_freeze and next_chain.stop == 1:
            # Do a few more ticks to verify freeze behavior
            # Actually, let's continue to see if it stays frozen
            pass
    
    stop_reached = current_counter.stop == 1
    
    return ChainSimulationResult(
        states=states,
        frames=frames,
        frames_compact=frames_compact,
        hit_wall_history=hit_wall_history,
        stop_history=stop_history,
        final_physics_state=current_physics,
        final_counter_state=current_counter,
        num_ticks=len(states) - 1,  # -1 because first state is initial
        stop_reached=stop_reached,
        freeze_tick=freeze_tick,
    )


def simulate_chain_with_ml_models(
    physics_model: torch.nn.Module,
    counter_model: torch.nn.Module,
    device: str = "cpu",
    max_ticks: int = 500,
) -> ChainSimulationResult:
    """
    Simulate chain using trained ML models.
    
    Args:
        physics_model: Trained physics model
        counter_model: Trained counter model
        device: Device to run models on
        max_ticks: Maximum number of ticks
    
    Returns:
        ChainSimulationResult
    """
    physics_fn = lambda s, stop: ml_physics_fn(physics_model, s, stop, device)
    counter_fn = lambda s, hit: ml_counter_fn(counter_model, s, hit, device)
    
    return simulate_chain(
        max_ticks=max_ticks,
        physics_fn=physics_fn,
        counter_fn=counter_fn,
    )


def simulate_chain_oracle() -> ChainSimulationResult:
    """
    Simulate chain using pure oracles (deterministic baseline).
    
    This is the reference implementation for acceptance gate 3.
    """
    return simulate_chain(
        max_ticks=500,
        physics_fn=oracle_physics_fn,
        counter_fn=oracle_counter_fn,
    )


def save_simulation_animation(
    result: ChainSimulationResult,
    output_dir: str | Path = "chain_animation",
) -> Path:
    """
    Save simulation frames as individual files for animation.
    
    Args:
        result: Chain simulation result
        output_dir: Directory to save frames
    
    Returns:
        Path to the output directory
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, frame in enumerate(result.frames):
        frame_path = output_dir / f"frame_{i:04d}.txt"
        frame_path.write_text(frame, encoding="utf-8")
    
    # Save metadata
    metadata = {
        "num_frames": len(result.frames),
        "final_counter": result.final_counter_state.count,
        "final_stop": result.final_counter_state.stop,
        "stop_reached": result.stop_reached,
        "freeze_tick": result.freeze_tick,
        "hit_wall_history": result.hit_wall_history,
        "stop_history": result.stop_history,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    return output_dir


# =============================================================================
# VISUALIZATION UTILITIES
# =============================================================================

def print_simulation_summary(result: ChainSimulationResult) -> None:
    """Print a summary of a chain simulation."""
    print(f"Simulation Summary:")
    print(f"  Total ticks: {result.num_ticks}")
    print(f"  Final physics state: {result.final_physics_state}")
    print(f"  Final counter state: count={result.final_counter_state.count}, stop={result.final_counter_state.stop}")
    print(f"  Stop reached: {result.stop_reached}")
    print(f"  Freeze tick: {result.freeze_tick}")
    print(f"  Total wall hits: {sum(result.hit_wall_history)}")
    print()


def print_simulation_frames(
    result: ChainSimulationResult,
    max_frames: int = 10,
    stride: int = 1,
) -> None:
    """Print a subset of frames from a simulation."""
    frames_to_show = min(max_frames, len(result.frames))
    
    for i in range(0, frames_to_show * stride, stride):
        if i >= len(result.frames):
            break
        frame = result.frames[i]
        counter = result.states[i].counter_state.count
        stop = result.states[i].counter_state.stop
        hit_wall = result.states[i].hit_wall if i > 0 else 0
        
        print(f"Tick {i}: count={counter}, stop={stop}, hit_wall={hit_wall}")
        print(frame)
        print()
