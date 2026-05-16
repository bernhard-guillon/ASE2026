"""
Deterministic Renderer for the Two-Model Squash Control Chain.

Renders a 20x20 grid frame as a string with:
- Walls: '#' (on all 4 borders)
- Ball: 'o' (single cell)
- Counter: '0'-'9' (top-left corner, row 0)
- Empty: ' ' (space)

This is the NON-ML rendering path as recommended in the handoff doc.
The renderer takes compact state objects and produces deterministic frame strings.
"""

from __future__ import annotations

from typing import Tuple

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    CounterState,
)


def render_frame(
    physics_state: PhysicsState,
    counter_state: CounterState,
) -> str:
    """
    Render a single 20x20 frame from physics and counter states.
    
    Args:
        physics_state: Current ball position and velocity
        counter_state: Current count and stop bit
    
    Returns:
        A string of exactly 20 lines, each with exactly 20 characters,
        representing the game state.
    """
    grid = [[' ' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    
    # Draw walls on all 4 borders
    for x in range(GRID_SIZE):
        grid[0][x] = '#'  # Top wall
        grid[GRID_SIZE - 1][x] = '#'  # Bottom wall
    for y in range(GRID_SIZE):
        grid[y][0] = '#'  # Left wall
        grid[y][GRID_SIZE - 1] = '#'  # Right wall
    
    # Draw counter in top-left corner (overrides wall at 0,0)
    # The handoff doc says "top-row character" - using position (0, 0)
    counter_char = str(counter_state.count)
    grid[0][0] = counter_char
    
    # Draw ball (overrides wall if at border)
    ball_y = physics_state.ball_y
    ball_x = physics_state.ball_x
    grid[ball_y][ball_x] = 'o'
    
    # Convert grid to string
    lines = [''.join(row) for row in grid]
    return '\n'.join(lines)


def render_frame_compact(
    physics_state: PhysicsState,
    counter_state: CounterState,
) -> str:
    """
    Render frame as a single line without newlines.
    Useful for logging or framebuffer formats.
    
    Returns:
        A single string of exactly 400 characters (20x20).
    """
    full_frame = render_frame(physics_state, counter_state)
    return full_frame.replace('\n', '')


def parse_frame(frame_str: str) -> Tuple[list[str], int, int]:
    """
    Parse a rendered frame to extract information.
    
    Args:
        frame_str: A frame string (with or without newlines)
    
    Returns:
        Tuple of (grid_lines, ball_x, ball_y) or (grid_lines, None, None) if no ball found
    """
    frame_str = frame_str.replace('\n', '')
    grid_size = int(len(frame_str) ** 0.5)
    
    lines = []
    for row in range(grid_size):
        start = row * grid_size
        end = start + grid_size
        lines.append(frame_str[start:end])
    
    # Find ball position
    ball_pos = None
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char == 'o':
                ball_pos = (x, y)
                break
        if ball_pos:
            break
    
    ball_x, ball_y = ball_pos if ball_pos else (None, None)
    return lines, ball_x, ball_y


def get_counter_char(frame_str: str) -> str:
    """
    Extract the counter character from a rendered frame.
    
    The counter is at position (0, 0) in the grid.
    """
    frame_str = frame_str.replace('\n', '')
    return frame_str[0]  # Top-left corner


# =============================================================================
# UTILITY FUNCTIONS FOR VISUALIZATION
# =============================================================================

def print_frame(physics_state: PhysicsState, counter_state: CounterState) -> None:
    """Print a rendered frame to stdout."""
    frame = render_frame(physics_state, counter_state)
    print(frame)
    print()  # Blank line after frame


def print_frame_sequence(
    physics_states: list[PhysicsState],
    counter_states: list[CounterState],
    frames_per_row: int = 5,
) -> None:
    """
    Print a sequence of frames in a grid layout.
    
    Args:
        physics_states: List of physics states (one per frame)
        counter_states: List of counter states (one per frame)
        frames_per_row: Number of frames to display per row
    """
    assert len(physics_states) == len(counter_states)
    
    for i, (p_state, c_state) in enumerate(zip(physics_states, counter_states)):
        frame = render_frame(p_state, c_state)
        lines = frame.split('\n')
        
        if i % frames_per_row == 0:
            # Start new set of rows
            for _ in range(GRID_SIZE):
                print()
        
        for row_idx, line in enumerate(lines):
            if i % frames_per_row == 0:
                # First frame in this group
                print(line, end='')
            else:
                # Subsequent frames - print at appropriate offset
                print(line, end='')
        
        print('  ', end='')  # Space between frames
    
    print()  # Final newline
