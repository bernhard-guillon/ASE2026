"""
Deterministic Counter Oracle for Model B (Hit Counter + Stop Trigger).

This module implements the deterministic oracle for the counter model.
The oracle counts wall hits and triggers a stop signal when reaching 9.

Counter behavior:
- Counts hit_wall pulses from Model A (0 to 9)
- stop bit is set to 1 once count reaches 9
- stop bit remains 1 (latched) even if more hit_wall pulses arrive
- If stop == 1, keep it asserted regardless of hit_wall input
"""

from __future__ import annotations

from typing import Tuple

from dual_model_contract import (
    CounterState,
    CounterStepResult,
)


def counter_oracle_step(
    state: CounterState,
    hit_wall: int,
) -> CounterStepResult:
    """
    Compute one deterministic counter step.
    
    Args:
        state: Current counter state (count + stop bit)
        hit_wall: Pulse bit from Model A (0 or 1)
    
    Returns:
        CounterStepResult containing the next counter state.
    
    Counter logic:
    1. If state.stop == 1, keep stop=1 and don't increment count (latched)
    2. If hit_wall == 1 and state.stop == 0:
       - Increment count by 1
       - If count reaches 9, set stop = 1
    3. If hit_wall == 0 and state.stop == 0:
       - Keep count unchanged, stop = 0
    """
    if hit_wall not in (0, 1):
        raise ValueError(f"hit_wall must be 0 or 1, got {hit_wall}")
    
    # If already stopped, stay stopped
    if state.stop == 1:
        next_state = CounterState(count=state.count, stop=1)
        return CounterStepResult(next_state=next_state)
    
    # Count hit_wall pulses
    new_count = state.count
    new_stop = 0
    
    if hit_wall == 1:
        new_count = state.count + 1
        # Check if we've reached the stop threshold
        if new_count >= 9:
            new_count = 9
            new_stop = 1
    
    next_state = CounterState(count=new_count, stop=new_stop)
    return CounterStepResult(next_state=next_state)


def simulate_counter_trajectory(
    initial_state: CounterState,
    hit_walls: list[int],
) -> list[CounterState]:
    """
    Simulate a trajectory of counter steps given a sequence of hit_wall bits.
    
    Args:
        initial_state: Starting counter state
        hit_walls: List of hit_wall bits (one per step) from Model A
    
    Returns:
        List of counter states after each step (including initial)
    """
    states = [initial_state]
    current_state = initial_state
    
    for hit_wall in hit_walls:
        result = counter_oracle_step(current_state, hit_wall)
        states.append(result.next_state)
        current_state = result.next_state
    
    return states


def count_to_rendering(state: CounterState) -> str:
    """
    Convert counter state to its rendered character.
    
    Returns '0' through '9' based on the count value.
    This is used for the deterministic renderer in D4.
    """
    return str(state.count)


# =============================================================================
# HELPER FUNCTIONS FOR TESTING / DEBUGGING
# =============================================================================

def test_count_to_nine(
    initial_state: CounterState = None,
) -> Tuple[list[CounterState], int]:
    """
    Test that counter reaches 9 and stops.
    
    Returns the trajectory and the step at which stop was triggered.
    """
    if initial_state is None:
        initial_state = CounterState(count=0, stop=0)
    
    # Send 10 hit_wall pulses
    hit_walls = [1] * 10
    states = simulate_counter_trajectory(initial_state, hit_walls)
    
    # Find when stop was triggered
    stop_step = None
    for i, s in enumerate(states):
        if s.stop == 1:
            stop_step = i
            break
    
    return states, stop_step


def test_latched_stop(
    initial_state: CounterState = None,
) -> list[CounterState]:
    """
    Test that once stop=1, it stays 1 even with more hit_wall pulses.
    """
    if initial_state is None:
        initial_state = CounterState(count=9, stop=0)
    
    # Send a bunch more hit_wall pulses after already being at 9
    hit_walls = [1] * 20
    return simulate_counter_trajectory(initial_state, hit_walls)


def test_no_increment_when_stopped(
    initial_state: CounterState = None,
) -> list[CounterState]:
    """
    Test that count doesn't increment when already stopped.
    """
    if initial_state is None:
        initial_state = CounterState(count=9, stop=1)
    
    hit_walls = [1] * 10
    return simulate_counter_trajectory(initial_state, hit_walls)
