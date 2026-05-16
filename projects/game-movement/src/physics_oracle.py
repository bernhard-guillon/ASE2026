"""
Deterministic Physics Oracle for Model A (Ball + Walls).

This module implements the deterministic oracle for ball physics on a 20x20 grid.
The oracle computes the next state and hit_wall bit given the current state and stop bit.

Ball dynamics:
- Moves at constant speed: 1 cell per tick
- Bounces on walls with reflection behavior
- If stop == 1, ball freezes (no movement)
- hit_wall is a pulse bit set to 1 only on the tick where collision occurs
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    PhysicsStepResult,
)


def physics_oracle_step(
    state: PhysicsState,
    stop_bit: int,
) -> PhysicsStepResult:
    """
    Compute one deterministic physics step.
    
    Args:
        state: Current physics state (ball position + velocity)
        stop_bit: Control bit from Model B (0 = continue, 1 = freeze)
    
    Returns:
        PhysicsStepResult containing:
        - next_state: The physics state after the step
        - hit_wall: 1 if wall collision occurred, 0 otherwise
    
    Physics logic:
    1. If stop_bit == 1, return current state unchanged with hit_wall=0
    2. Compute next position: (ball_x + vel_x, ball_y + vel_y)
    3. If next position is out of bounds:
       - Reflect velocity (negate the component that hit the wall)
       - Clamp position to valid bounds
       - Set hit_wall = 1
    4. Otherwise, keep velocity unchanged, hit_wall = 0
    """
    if stop_bit not in (0, 1):
        raise ValueError(f"stop_bit must be 0 or 1, got {stop_bit}")
    
    if stop_bit == 1:
        # Ball is frozen - no movement, no wall hit
        return PhysicsStepResult(next_state=state, hit_wall=0)
    
    # Compute tentative next position
    next_x = state.ball_x + state.vel_x
    next_y = state.ball_y + state.vel_y
    
    # Check for wall collision
    hit_wall = 0
    new_vel_x = state.vel_x
    new_vel_y = state.vel_y
    
    # Check X bounds
    if next_x < 0:
        # Hit left wall - reflect X velocity
        next_x = 0
        new_vel_x = -state.vel_x
        hit_wall = 1
    elif next_x >= GRID_SIZE:
        # Hit right wall - reflect X velocity
        next_x = GRID_SIZE - 1
        new_vel_x = -state.vel_x
        hit_wall = 1
    
    # Check Y bounds
    if next_y < 0:
        # Hit top wall - reflect Y velocity
        next_y = 0
        new_vel_y = -state.vel_y
        hit_wall = 1
    elif next_y >= GRID_SIZE:
        # Hit bottom wall - reflect Y velocity
        next_y = GRID_SIZE - 1
        new_vel_y = -state.vel_y
        hit_wall = 1
    
    next_state = PhysicsState(
        ball_x=next_x,
        ball_y=next_y,
        vel_x=new_vel_x,
        vel_y=new_vel_y,
    )
    
    return PhysicsStepResult(next_state=next_state, hit_wall=hit_wall)


def simulate_physics_trajectory(
    initial_state: PhysicsState,
    stop_bits: list[int],
) -> Tuple[list[PhysicsState], list[int]]:
    """
    Simulate a trajectory of physics steps given a sequence of stop bits.
    
    Args:
        initial_state: Starting physics state
        stop_bits: List of stop bits (one per step) from Model B
    
    Returns:
        Tuple of (list of states after each step, list of hit_wall bits)
    """
    states = [initial_state]
    hit_walls = []
    current_state = initial_state
    
    for stop_bit in stop_bits:
        result = physics_oracle_step(current_state, stop_bit)
        states.append(result.next_state)
        hit_walls.append(result.hit_wall)
        current_state = result.next_state
    
    return states, hit_walls
