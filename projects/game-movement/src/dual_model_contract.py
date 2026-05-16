"""
Dual Model Contracts for Two-Model Squash Control Chain

This module defines the explicit contracts/interfaces for Model A (Physics) and Model B (Counter).
All state vectors, bit semantics, and tick semantics are documented here.

Architecture Overview:
    Model A (Physics): Simulates ball movement on a 20x20 grid with wall collisions
    Model B (Counter): Counts wall hits and triggers stop at count 9
    
    Closed-loop tick order:
        1. Model A step -> produces hit_wall bit
        2. Model B step (with hit_wall) -> produces stop bit  
        3. Feed stop bit into next Model A step
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

# =============================================================================
# GLOBAL CONSTANTS
# =============================================================================

GRID_SIZE: int = 20
"""The size of the square grid: 20x20 cells."""

# =============================================================================
# MODEL A: PHYSICS MODEL CONTRACT
# =============================================================================

@dataclass(frozen=True)
class PhysicsState:
    """
    State vector for Model A (Physics Model).
    
    Represents the complete state of the ball on the grid.
    
    Attributes:
        ball_x: X coordinate of the ball (0 to GRID_SIZE-1)
        ball_y: Y coordinate of the ball (0 to GRID_SIZE-1)
        vel_x: X velocity component (-1, 0, or 1)
        vel_y: Y velocity component (-1, 0, or 1)
    
    Note: The ball moves at exactly 1 cell per tick, so at least one of vel_x or vel_y
    is non-zero. The velocity vector is normalized such that ||vel|| = 1 (Manhattan).
    Diagonal movement is NOT allowed - exactly one of vel_x or vel_y is non-zero.
    """
    ball_x: int
    ball_y: int
    vel_x: int
    vel_y: int
    
    def __post_init__(self):
        # Validate position bounds
        if not (0 <= self.ball_x < GRID_SIZE):
            raise ValueError(f"ball_x must be in [0, {GRID_SIZE-1}], got {self.ball_x}")
        if not (0 <= self.ball_y < GRID_SIZE):
            raise ValueError(f"ball_y must be in [0, {GRID_SIZE-1}], got {self.ball_y}")
        
        # Validate velocity (Manhattan norm = 1, no diagonal)
        if not (self.vel_x in (-1, 0, 1) and self.vel_y in (-1, 0, 1)):
            raise ValueError(f"Velocity components must be in {-1, 0, 1}, got ({self.vel_x}, {self.vel_y})")
        if abs(self.vel_x) + abs(self.vel_y) != 1:
            raise ValueError(f"Exactly one velocity component must be non-zero (Manhattan norm = 1), got ({self.vel_x}, {self.vel_y})")


@dataclass(frozen=True)
class PhysicsStepResult:
    """
    Result of a single physics step.
    
    Attributes:
        next_state: The physics state after the step
        hit_wall: Pulse bit (0 or 1). Set to 1 if the ball collided with a wall during this step.
                  Only set for the single tick where the collision occurs.
    """
    next_state: PhysicsState
    hit_wall: int  # 0 or 1
    
    def __post_init__(self):
        if self.hit_wall not in (0, 1):
            raise ValueError(f"hit_wall must be 0 or 1, got {self.hit_wall}")


# =============================================================================
# MODEL B: COUNTER MODEL CONTRACT
# =============================================================================

@dataclass(frozen=True)
class CounterState:
    """
    State vector for Model B (Counter Model).
    
    Attributes:
        count: The current hit count (0 to 9)
        stop: The stop bit (0 or 1). Once set to 1, it remains 1 (latched).
    """
    count: int
    stop: int  # 0 or 1
    
    def __post_init__(self):
        if not (0 <= self.count <= 9):
            raise ValueError(f"count must be in [0, 9], got {self.count}")
        if self.stop not in (0, 1):
            raise ValueError(f"stop must be 0 or 1, got {self.stop}")


@dataclass(frozen=True)
class CounterStepResult:
    """
    Result of a single counter step.
    
    Attributes:
        next_state: The counter state after the step
    """
    next_state: CounterState


# =============================================================================
# BIT SEMANTICS
# =============================================================================

# hit_wall bit (from Model A to Model B):
#   - 0: No wall collision occurred in this physics step
#   - 1: A wall collision occurred in this physics step (pulse, only for that tick)
#
# stop bit (from Model B to Model A):
#   - 0: Continue normal physics simulation
#   - 1: Freeze the ball (no movement updates in Model A)
#   - Once stop becomes 1, it stays 1 (latched behavior)

# =============================================================================
# RESET / INITIALIZATION SEMANTICS
# =============================================================================

def default_physics_state() -> PhysicsState:
    """
    Default initial physics state.
    Ball starts at position (1, 1) with velocity right (1, 0).
    """
    return PhysicsState(ball_x=1, ball_y=1, vel_x=1, vel_y=0)


def default_counter_state() -> CounterState:
    """
    Default initial counter state.
    Counter starts at 0, stop bit is 0 (not stopped).
    """
    return CounterState(count=0, stop=0)


# =============================================================================
# STATE ENCODING / DECODING (for ML interface)
# =============================================================================

def encode_physics_state(state: PhysicsState) -> np.ndarray:
    """
    Encode a PhysicsState into a dense vector for model input.
    
    Encoding scheme:
    - ball_x: one-hot over GRID_SIZE buckets (20)
    - ball_y: one-hot over GRID_SIZE buckets (20)
    - vel_x: one-hot over 3 buckets (-1, 0, 1)
    - vel_y: one-hot over 3 buckets (-1, 0, 1)
    
    Total: 20 + 20 + 3 + 3 = 46 elements
    """
    encoding = []
    
    # ball_x one-hot
    x_onehot = np.zeros(GRID_SIZE, dtype=np.float32)
    x_onehot[state.ball_x] = 1.0
    encoding.append(x_onehot)
    
    # ball_y one-hot
    y_onehot = np.zeros(GRID_SIZE, dtype=np.float32)
    y_onehot[state.ball_y] = 1.0
    encoding.append(y_onehot)
    
    # vel_x one-hot (index 0=-1, 1=0, 2=1)
    vel_x_onehot = np.zeros(3, dtype=np.float32)
    vel_x_onehot[state.vel_x + 1] = 1.0  # map -1->0, 0->1, 1->2
    encoding.append(vel_x_onehot)
    
    # vel_y one-hot (index 0=-1, 1=0, 2=1)
    vel_y_onehot = np.zeros(3, dtype=np.float32)
    vel_y_onehot[state.vel_y + 1] = 1.0
    encoding.append(vel_y_onehot)
    
    return np.concatenate(encoding)


def decode_physics_state(encoding: np.ndarray) -> PhysicsState:
    """
    Decode a dense vector back into a PhysicsState.
    
    Reverse of encode_physics_state.
    """
    encoding = np.asarray(encoding, dtype=np.float32)
    expected_len = GRID_SIZE + GRID_SIZE + 3 + 3
    if len(encoding) != expected_len:
        raise ValueError(f"Expected encoding length {expected_len}, got {len(encoding)}")
    
    parts = []
    offset = 0
    parts.append(encoding[offset:offset + GRID_SIZE]); offset += GRID_SIZE  # ball_x
    parts.append(encoding[offset:offset + GRID_SIZE]); offset += GRID_SIZE  # ball_y
    parts.append(encoding[offset:offset + 3]); offset += 3  # vel_x
    parts.append(encoding[offset:offset + 3]); offset += 3  # vel_y
    
    ball_x = int(np.argmax(parts[0]))
    ball_y = int(np.argmax(parts[1]))
    vel_x = int(np.argmax(parts[2])) - 1  # map 0->-1, 1->0, 2->1
    vel_y = int(np.argmax(parts[3])) - 1
    
    return PhysicsState(ball_x=ball_x, ball_y=ball_y, vel_x=vel_x, vel_y=vel_y)


def encode_counter_state(state: CounterState) -> np.ndarray:
    """
    Encode a CounterState into a dense vector for model input.
    
    Encoding scheme:
    - count: one-hot over 10 buckets (0-9)
    - stop: single bit (0 or 1)
    
    Total: 10 + 1 = 11 elements
    """
    count_onehot = np.zeros(10, dtype=np.float32)
    count_onehot[state.count] = 1.0
    stop_bit = np.array([state.stop], dtype=np.float32)
    return np.concatenate([count_onehot, stop_bit])


def decode_counter_state(encoding: np.ndarray) -> CounterState:
    """
    Decode a dense vector back into a CounterState.
    
    Reverse of encode_counter_state.
    """
    encoding = np.asarray(encoding, dtype=np.float32)
    if len(encoding) != 11:
        raise ValueError(f"Expected encoding length 11, got {len(encoding)}")
    
    count_onehot = encoding[:10]
    stop_bit = encoding[10]
    
    count = int(np.argmax(count_onehot))
    stop = int(np.round(stop_bit))
    
    return CounterState(count=count, stop=stop)


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def physics_step_input(state: PhysicsState, stop_bit: int) -> np.ndarray:
    """
    Construct the full input vector for Model A.
    
    Combines encoded physics state with the stop bit from Model B.
    
    Total: 46 (state) + 1 (stop) = 47 elements
    """
    state_encoding = encode_physics_state(state)
    stop_vec = np.array([stop_bit], dtype=np.float32)
    return np.concatenate([state_encoding, stop_vec])


def counter_step_input(state: CounterState, hit_wall: int) -> np.ndarray:
    """
    Construct the full input vector for Model B.
    
    Combines encoded counter state with the hit_wall bit from Model A.
    
    Total: 11 (state) + 1 (hit_wall) = 12 elements
    """
    state_encoding = encode_counter_state(state)
    hit_wall_vec = np.array([hit_wall], dtype=np.float32)
    return np.concatenate([state_encoding, hit_wall_vec])
