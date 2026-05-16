"""
Unit tests for the physics oracle (Model A).

Tests cover:
- Basic movement in all 4 cardinal directions
- Wall collision and bounce behavior
- Corner collision behavior
- Freeze behavior when stop_bit = 1
- Deterministic encoding/decoding
"""

import unittest

import numpy as np

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    PhysicsStepResult,
    encode_physics_state,
    decode_physics_state,
    physics_step_input,
    default_physics_state,
)
from physics_oracle import (
    physics_oracle_step,
    simulate_physics_trajectory,
)


class PhysicsStateTests(unittest.TestCase):
    """Tests for PhysicsState validation and construction."""
    
    def test_valid_states(self):
        # Valid states with all 4 cardinal directions
        for vel_x, vel_y in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            for x in [0, 10, GRID_SIZE - 1]:
                for y in [0, 10, GRID_SIZE - 1]:
                    state = PhysicsState(ball_x=x, ball_y=y, vel_x=vel_x, vel_y=vel_y)
                    self.assertEqual(state.ball_x, x)
                    self.assertEqual(state.ball_y, y)
                    self.assertEqual(state.vel_x, vel_x)
                    self.assertEqual(state.vel_y, vel_y)
    
    def test_invalid_velocity_diagonal(self):
        with self.assertRaises(ValueError):
            PhysicsState(ball_x=0, ball_y=0, vel_x=1, vel_y=1)
    
    def test_invalid_velocity_zero(self):
        with self.assertRaises(ValueError):
            PhysicsState(ball_x=0, ball_y=0, vel_x=0, vel_y=0)
    
    def test_invalid_velocity_out_of_range(self):
        with self.assertRaises(ValueError):
            PhysicsState(ball_x=0, ball_y=0, vel_x=2, vel_y=0)
    
    def test_invalid_position_out_of_bounds(self):
        with self.assertRaises(ValueError):
            PhysicsState(ball_x=GRID_SIZE, ball_y=0, vel_x=1, vel_y=0)
        with self.assertRaises(ValueError):
            PhysicsState(ball_x=0, ball_y=GRID_SIZE, vel_x=1, vel_y=0)


class PhysicsOracleTests(unittest.TestCase):
    """Tests for the physics oracle step function."""
    
    def test_free_movement_right(self):
        """Ball moving right in free space."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 6)
        self.assertEqual(result.next_state.ball_y, 5)
        self.assertEqual(result.next_state.vel_x, 1)
        self.assertEqual(result.next_state.vel_y, 0)
        self.assertEqual(result.hit_wall, 0)
    
    def test_free_movement_left(self):
        """Ball moving left in free space."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=-1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 4)
        self.assertEqual(result.next_state.ball_y, 5)
        self.assertEqual(result.next_state.vel_x, -1)
        self.assertEqual(result.hit_wall, 0)
    
    def test_free_movement_down(self):
        """Ball moving down in free space."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=0, vel_y=1)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 5)
        self.assertEqual(result.next_state.ball_y, 6)
        self.assertEqual(result.next_state.vel_y, 1)
        self.assertEqual(result.hit_wall, 0)
    
    def test_free_movement_up(self):
        """Ball moving up in free space."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=0, vel_y=-1)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 5)
        self.assertEqual(result.next_state.ball_y, 4)
        self.assertEqual(result.next_state.vel_y, -1)
        self.assertEqual(result.hit_wall, 0)
    
    def test_bounce_right_wall(self):
        """Ball bounces off right wall."""
        state = PhysicsState(ball_x=GRID_SIZE - 1, ball_y=5, vel_x=1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=0)
        
        # Ball should be at rightmost position, velocity reflected
        self.assertEqual(result.next_state.ball_x, GRID_SIZE - 1)
        self.assertEqual(result.next_state.ball_y, 5)
        self.assertEqual(result.next_state.vel_x, -1)
        self.assertEqual(result.hit_wall, 1)
    
    def test_bounce_left_wall(self):
        """Ball bounces off left wall."""
        state = PhysicsState(ball_x=0, ball_y=5, vel_x=-1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 0)
        self.assertEqual(result.next_state.ball_y, 5)
        self.assertEqual(result.next_state.vel_x, 1)
        self.assertEqual(result.hit_wall, 1)
    
    def test_bounce_top_wall(self):
        """Ball bounces off top wall."""
        state = PhysicsState(ball_x=5, ball_y=0, vel_x=0, vel_y=-1)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 5)
        self.assertEqual(result.next_state.ball_y, 0)
        self.assertEqual(result.next_state.vel_y, 1)
        self.assertEqual(result.hit_wall, 1)
    
    def test_bounce_bottom_wall(self):
        """Ball bounces off bottom wall."""
        state = PhysicsState(ball_x=5, ball_y=GRID_SIZE - 1, vel_x=0, vel_y=1)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, 5)
        self.assertEqual(result.next_state.ball_y, GRID_SIZE - 1)
        self.assertEqual(result.next_state.vel_y, -1)
        self.assertEqual(result.hit_wall, 1)
    
    def test_no_wall_hit_near_boundary(self):
        """Ball near wall but not hitting it."""
        # One cell away from right wall, moving right - should NOT hit wall yet
        state = PhysicsState(ball_x=GRID_SIZE - 2, ball_y=5, vel_x=1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=0)
        
        self.assertEqual(result.next_state.ball_x, GRID_SIZE - 1)
        self.assertEqual(result.hit_wall, 0)
    
    def test_freeze_when_stopped(self):
        """Ball freezes when stop_bit = 1."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=1)
        
        # State should be unchanged
        self.assertEqual(result.next_state.ball_x, 5)
        self.assertEqual(result.next_state.ball_y, 5)
        self.assertEqual(result.next_state.vel_x, 1)
        self.assertEqual(result.next_state.vel_y, 0)
        # No wall hit when frozen
        self.assertEqual(result.hit_wall, 0)
    
    def test_freeze_at_wall(self):
        """Ball at wall with stop_bit=1 doesn't bounce."""
        state = PhysicsState(ball_x=GRID_SIZE - 1, ball_y=5, vel_x=1, vel_y=0)
        result = physics_oracle_step(state, stop_bit=1)
        
        # Should stay at wall, not bounce
        self.assertEqual(result.next_state.ball_x, GRID_SIZE - 1)
        self.assertEqual(result.next_state.vel_x, 1)  # velocity unchanged
        self.assertEqual(result.hit_wall, 0)
    
    def test_invalid_stop_bit(self):
        """Raises error for invalid stop_bit."""
        state = default_physics_state()
        with self.assertRaises(ValueError):
            physics_oracle_step(state, stop_bit=2)
        with self.assertRaises(ValueError):
            physics_oracle_step(state, stop_bit=-1)


class PhysicsEncodingTests(unittest.TestCase):
    """Tests for physics state encoding/decoding."""
    
    def test_encode_decode_roundtrip(self):
        """Encoding and decoding should be inverse operations."""
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                for vel_x, vel_y in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    state = PhysicsState(
                        ball_x=x,
                        ball_y=y,
                        vel_x=vel_x,
                        vel_y=vel_y,
                    )
                    encoded = encode_physics_state(state)
                    decoded = decode_physics_state(encoded)
                    
                    self.assertEqual(decoded.ball_x, state.ball_x)
                    self.assertEqual(decoded.ball_y, state.ball_y)
                    self.assertEqual(decoded.vel_x, state.vel_x)
                    self.assertEqual(decoded.vel_y, state.vel_y)
    
    def test_encoding_shape(self):
        """Encoding should produce vector of expected length."""
        state = default_physics_state()
        encoded = encode_physics_state(state)
        # 20 (ball_x) + 20 (ball_y) + 3 (vel_x) + 3 (vel_y) = 46
        self.assertEqual(len(encoded), 46)
    
    def test_step_input_shape(self):
        """Full step input should have expected shape."""
        state = default_physics_state()
        for stop_bit in [0, 1]:
            input_vec = physics_step_input(state, stop_bit)
            # 46 (state) + 1 (stop) = 47
            self.assertEqual(len(input_vec), 47)


class PhysicsTrajectoryTests(unittest.TestCase):
    """Tests for trajectory simulation."""
    
    def test_horizontal_bounce_cycle(self):
        """Ball bounces between left and right walls."""
        initial = PhysicsState(ball_x=1, ball_y=5, vel_x=1, vel_y=0)
        stop_bits = [0] * 40  # 40 steps of movement
        
        states, hit_walls = simulate_physics_trajectory(initial, stop_bits)
        
        # First hit should be at right wall (x=19)
        # Ball starts at x=1, moves right -> hits at x=19 after 18 steps
        # Then bounces back, hits left wall (x=0) after another 19 steps
        # Then bounces right again
        
        # Check we got some wall hits
        self.assertGreater(sum(hit_walls), 0)
        
        # All states should be valid
        for s in states:
            self.assertGreaterEqual(s.ball_x, 0)
            self.assertLess(s.ball_x, GRID_SIZE)
            self.assertGreaterEqual(s.ball_y, 5)
            self.assertLess(s.ball_y, GRID_SIZE)
    
    def test_vertical_bounce_cycle(self):
        """Ball bounces between top and bottom walls."""
        initial = PhysicsState(ball_x=5, ball_y=1, vel_x=0, vel_y=1)
        stop_bits = [0] * 40
        
        states, hit_walls = simulate_physics_trajectory(initial, stop_bits)
        
        self.assertGreater(sum(hit_walls), 0)
    
    def test_freeze_trajectory(self):
        """Ball freezes after stop_bit becomes 1."""
        initial = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        # Freeze after 5 steps
        stop_bits = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
        
        states, hit_walls = simulate_physics_trajectory(initial, stop_bits)
        
        # After step 5 (index 5 in stop_bits), ball should be frozen
        # states[0] = initial
        # states[1] = after step 0
        # ...
        # states[6] = after step 5 (first with stop=1)
        
        # From step 6 onwards, position shouldn't change
        for i in range(6, len(states)):
            self.assertEqual(states[i].ball_x, states[5].ball_x)
            self.assertEqual(states[i].ball_y, states[5].ball_y)
            self.assertEqual(states[i].vel_x, states[5].vel_x)
            self.assertEqual(states[i].vel_y, states[5].vel_y)


class PhysicsStepResultTests(unittest.TestCase):
    """Tests for PhysicsStepResult validation."""
    
    def test_valid_hit_wall_values(self):
        state = default_physics_state()
        for hit_wall in [0, 1]:
            result = PhysicsStepResult(next_state=state, hit_wall=hit_wall)
            self.assertEqual(result.hit_wall, hit_wall)
    
    def test_invalid_hit_wall(self):
        state = default_physics_state()
        with self.assertRaises(ValueError):
            PhysicsStepResult(next_state=state, hit_wall=2)
        with self.assertRaises(ValueError):
            PhysicsStepResult(next_state=state, hit_wall=-1)


if __name__ == "__main__":
    unittest.main()
