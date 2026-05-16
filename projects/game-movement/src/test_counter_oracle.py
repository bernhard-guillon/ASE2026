"""
Unit tests for the counter oracle (Model B).

Tests cover:
- Counting hit_wall pulses from 0 to 9
- Stop bit triggering at count 9
- Latch behavior (stop remains 1 once set)
- No increment when already stopped
- Deterministic encoding/decoding
"""

import unittest

import numpy as np

from dual_model_contract import (
    CounterState,
    CounterStepResult,
    encode_counter_state,
    decode_counter_state,
    counter_step_input,
    default_counter_state,
)
from counter_oracle import (
    counter_oracle_step,
    simulate_counter_trajectory,
    count_to_rendering,
)


class CounterStateTests(unittest.TestCase):
    """Tests for CounterState validation and construction."""
    
    def test_valid_states(self):
        """All valid counter states should be constructible."""
        for count in range(10):
            for stop in [0, 1]:
                state = CounterState(count=count, stop=stop)
                self.assertEqual(state.count, count)
                self.assertEqual(state.stop, stop)
    
    def test_invalid_count_negative(self):
        """Negative count should raise error."""
        with self.assertRaises(ValueError):
            CounterState(count=-1, stop=0)
    
    def test_invalid_count_over_nine(self):
        """Count > 9 should raise error."""
        with self.assertRaises(ValueError):
            CounterState(count=10, stop=0)
    
    def test_invalid_stop_bit(self):
        """Stop bit not in {0, 1} should raise error."""
        with self.assertRaises(ValueError):
            CounterState(count=0, stop=2)
        with self.assertRaises(ValueError):
            CounterState(count=0, stop=-1)


class CounterOracleTests(unittest.TestCase):
    """Tests for the counter oracle step function."""
    
    def test_count_increment_on_hit(self):
        """Counter increments when hit_wall = 1."""
        state = CounterState(count=0, stop=0)
        result = counter_oracle_step(state, hit_wall=1)
        
        self.assertEqual(result.next_state.count, 1)
        self.assertEqual(result.next_state.stop, 0)
    
    def test_no_increment_on_no_hit(self):
        """Counter stays same when hit_wall = 0."""
        state = CounterState(count=5, stop=0)
        result = counter_oracle_step(state, hit_wall=0)
        
        self.assertEqual(result.next_state.count, 5)
        self.assertEqual(result.next_state.stop, 0)
    
    def test_count_to_nine(self):
        """Counter reaches 9 and sets stop=1."""
        state = CounterState(count=8, stop=0)
        result = counter_oracle_step(state, hit_wall=1)
        
        self.assertEqual(result.next_state.count, 9)
        self.assertEqual(result.next_state.stop, 1)
    
    def test_stop_at_nine_clamped(self):
        """Counter doesn't go beyond 9."""
        state = CounterState(count=9, stop=0)
        result = counter_oracle_step(state, hit_wall=1)
        
        self.assertEqual(result.next_state.count, 9)
        self.assertEqual(result.next_state.stop, 1)
    
    def test_latched_stop_remains_one(self):
        """Once stop=1, it stays 1."""
        state = CounterState(count=9, stop=1)
        result = counter_oracle_step(state, hit_wall=0)
        
        self.assertEqual(result.next_state.count, 9)
        self.assertEqual(result.next_state.stop, 1)
    
    def test_latched_stop_ignores_hits(self):
        """Once stopped, more hits don't increment count."""
        state = CounterState(count=9, stop=1)
        result = counter_oracle_step(state, hit_wall=1)
        
        self.assertEqual(result.next_state.count, 9)
        self.assertEqual(result.next_state.stop, 1)
    
    def test_stop_zero_stays_zero(self):
        """If stop=0 and no hit, stays at 0."""
        state = CounterState(count=0, stop=0)
        result = counter_oracle_step(state, hit_wall=0)
        
        self.assertEqual(result.next_state.count, 0)
        self.assertEqual(result.next_state.stop, 0)
    
    def test_invalid_hit_wall(self):
        """Raises error for invalid hit_wall."""
        state = default_counter_state()
        with self.assertRaises(ValueError):
            counter_oracle_step(state, hit_wall=2)
        with self.assertRaises(ValueError):
            counter_oracle_step(state, hit_wall=-1)
    
    def test_full_count_sequence(self):
        """Count from 0 to 9 with sequential hits."""
        state = CounterState(count=0, stop=0)
        
        for expected_count in range(1, 10):
            result = counter_oracle_step(state, hit_wall=1)
            state = result.next_state
            self.assertEqual(state.count, expected_count)
        
        # At 9, stop should be set
        self.assertEqual(state.stop, 1)


class CounterEncodingTests(unittest.TestCase):
    """Tests for counter state encoding/decoding."""
    
    def test_encode_decode_roundtrip(self):
        """Encoding and decoding should be inverse operations."""
        for count in range(10):
            for stop in [0, 1]:
                state = CounterState(count=count, stop=stop)
                encoded = encode_counter_state(state)
                decoded = decode_counter_state(encoded)
                
                self.assertEqual(decoded.count, state.count)
                self.assertEqual(decoded.stop, state.stop)
    
    def test_encoding_shape(self):
        """Encoding should produce vector of expected length."""
        state = default_counter_state()
        encoded = encode_counter_state(state)
        # 10 (count one-hot) + 1 (stop) = 11
        self.assertEqual(len(encoded), 11)
    
    def test_step_input_shape(self):
        """Full step input should have expected shape."""
        state = default_counter_state()
        for hit_wall in [0, 1]:
            input_vec = counter_step_input(state, hit_wall)
            # 11 (state) + 1 (hit_wall) = 12
            self.assertEqual(len(input_vec), 12)


class CounterTrajectoryTests(unittest.TestCase):
    """Tests for trajectory simulation."""
    
    def test_count_to_nine_trajectory(self):
        """Counter reaches 9 and stops over trajectory."""
        initial = CounterState(count=0, stop=0)
        hit_walls = [1] * 15  # 15 hit pulses
        
        states = simulate_counter_trajectory(initial, hit_walls)
        
        # Check count increases
        counts = [s.count for s in states]
        self.assertEqual(counts[0], 0)
        self.assertEqual(counts[1], 1)
        self.assertEqual(counts[9], 9)
        
        # Check stop is set at count 9
        for i, s in enumerate(states):
            if s.count >= 9:
                self.assertEqual(s.stop, 1)
                # All subsequent states should also have stop=1
                for j in range(i, len(states)):
                    self.assertEqual(states[j].stop, 1)
                break
    
    def test_no_hits_no_change(self):
        """No hit_wall pulses means count stays at 0."""
        initial = CounterState(count=0, stop=0)
        hit_walls = [0] * 10
        
        states = simulate_counter_trajectory(initial, hit_walls)
        
        for s in states:
            self.assertEqual(s.count, 0)
            self.assertEqual(s.stop, 0)
    
    def test_already_stopped_trajectory(self):
        """Already stopped counter doesn't change."""
        initial = CounterState(count=9, stop=1)
        hit_walls = [1, 0, 1, 0, 1] * 3
        
        states = simulate_counter_trajectory(initial, hit_walls)
        
        for s in states:
            self.assertEqual(s.count, 9)
            self.assertEqual(s.stop, 1)


class CounterStepResultTests(unittest.TestCase):
    """Tests for CounterStepResult validation."""
    
    def test_result_contains_next_state(self):
        """Step result should contain next state."""
        state = default_counter_state()
        result = counter_oracle_step(state, hit_wall=1)
        
        self.assertIsInstance(result.next_state, CounterState)
        self.assertEqual(result.next_state.count, 1)


class CounterRenderingTests(unittest.TestCase):
    """Tests for counter rendering helper."""
    
    def test_rendering_all_counts(self):
        """Each count should render to its string digit."""
        for count in range(10):
            state = CounterState(count=count, stop=0)
            rendered = count_to_rendering(state)
            self.assertEqual(rendered, str(count))
    
    def test_rendering_at_nine(self):
        """Count 9 with stop=1 should render as '9'."""
        state = CounterState(count=9, stop=1)
        rendered = count_to_rendering(state)
        self.assertEqual(rendered, "9")


class IntegrationTests(unittest.TestCase):
    """Integration tests combining physics and counter oracles."""
    
    def test_closed_loop_reaches_stop(self):
        """
        Test that a closed-loop system (physics -> counter -> physics) 
        reaches stop at count 9.
        
        This is a pure-oracle test using the oracles directly.
        """
        from physics_oracle import physics_oracle_step
        from dual_model_contract import PhysicsState
        
        # Initial states
        physics_state = PhysicsState(ball_x=1, ball_y=1, vel_x=1, vel_y=0)
        counter_state = CounterState(count=0, stop=0)
        
        max_steps = 200
        stop_reached = False
        
        for _ in range(max_steps):
            # Step 1: Physics step
            physics_result = physics_oracle_step(physics_state, counter_state.stop)
            physics_state = physics_result.next_state
            hit_wall = physics_result.hit_wall
            
            # Step 2: Counter step
            counter_result = counter_oracle_step(counter_state, hit_wall)
            counter_state = counter_result.next_state
            
            # Check if we've reached stop
            if counter_state.stop == 1:
                stop_reached = True
                break
        
        self.assertTrue(stop_reached, "Stop was never reached within max_steps")
        self.assertEqual(counter_state.count, 9)
        self.assertEqual(counter_state.stop, 1)


if __name__ == "__main__":
    unittest.main()
