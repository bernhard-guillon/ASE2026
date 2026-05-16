"""
Unit tests for the chain integrator (D4 acceptance gates).

Tests verify:
1. Pure-oracle integrated simulation reaches stop at count 9
2. Ball freezes when stop is asserted
3. Counter increments on wall collisions
4. Deterministic rendering produces correct frames
"""

import unittest

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    CounterState,
    default_physics_state,
    default_counter_state,
)
from chain_integrator import (
    chain_step,
    simulate_chain,
    simulate_chain_oracle,
    ChainState,
    ChainStepResult,
    ChainSimulationResult,
)
from deterministic_renderer import (
    render_frame,
    render_frame_compact,
    parse_frame,
    get_counter_char,
)


class RendererTests(unittest.TestCase):
    """Tests for the deterministic renderer."""
    
    def test_frame_dimensions(self):
        """Rendered frame should be 20x20."""
        state = default_physics_state()
        counter = default_counter_state()
        frame = render_frame(state, counter)
        
        lines = frame.split('\n')
        self.assertEqual(len(lines), GRID_SIZE)
        for line in lines:
            self.assertEqual(len(line), GRID_SIZE)
    
    def test_compact_frame_length(self):
        """Compact frame should be exactly 400 characters."""
        state = default_physics_state()
        counter = default_counter_state()
        frame = render_frame_compact(state, counter)
        self.assertEqual(len(frame), GRID_SIZE * GRID_SIZE)
    
    def test_walls_present(self):
        """All border cells should be walls (#) except counter at (0,0)."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        counter = CounterState(count=0, stop=0)
        frame = render_frame(state, counter)
        lines = frame.split('\n')
        
        # Check top row - except (0,0) which has counter
        for x in range(1, GRID_SIZE):
            self.assertEqual(lines[0][x], '#')  # Top wall (except counter at 0,0)
        
        # Check bottom row
        for x in range(GRID_SIZE):
            self.assertEqual(lines[GRID_SIZE-1][x], '#')  # Bottom wall
        
        # Check left column - except (0,0) which has counter
        for y in range(1, GRID_SIZE):
            self.assertEqual(lines[y][0], '#')  # Left wall (except counter at 0,0)
        
        # Check right column
        for y in range(GRID_SIZE):
            self.assertEqual(lines[y][GRID_SIZE-1], '#')  # Right wall
    
    def test_ball_rendered(self):
        """Ball should be rendered as 'o' at correct position."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        counter = CounterState(count=0, stop=0)
        frame = render_frame(state, counter)
        lines = frame.split('\n')
        
        self.assertEqual(lines[5][5], 'o')
    
    def test_counter_rendered(self):
        """Counter should be rendered at top-left corner."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        counter = CounterState(count=3, stop=0)
        frame = render_frame(state, counter)
        
        self.assertEqual(frame[0], '3')  # First character should be counter
    
    def test_counter_overrides_wall(self):
        """Counter at (0,0) should override wall."""
        state = PhysicsState(ball_x=5, ball_y=5, vel_x=1, vel_y=0)
        counter = CounterState(count=7, stop=0)
        frame = render_frame(state, counter)
        
        self.assertEqual(frame[0], '7')
    
    def test_ball_overrides_wall(self):
        """Ball at wall position should override wall."""
        # Ball at (0, 5) - on left wall
        state = PhysicsState(ball_x=0, ball_y=5, vel_x=1, vel_y=0)
        counter = CounterState(count=0, stop=0)
        frame = render_frame(state, counter)
        lines = frame.split('\n')
        
        self.assertEqual(lines[5][0], 'o')


class ChainStepTests(unittest.TestCase):
    """Tests for individual chain steps."""
    
    def test_initial_step(self):
        """First step from default states."""
        state = default_physics_state()  # (1, 1) moving right
        counter = default_counter_state()  # count=0, stop=0
        
        result = chain_step(state, counter)
        
        self.assertIsInstance(result, ChainStepResult)
        self.assertIsInstance(result.next_chain_state, ChainState)
        self.assertEqual(len(result.frame), GRID_SIZE * (GRID_SIZE + 1) - 1)  # 20 lines of 20 + 19 newlines
        self.assertEqual(len(result.frame_compact), GRID_SIZE * GRID_SIZE)


class ChainSimulationTests(unittest.TestCase):
    """Tests for full chain simulation."""
    
    def test_reaches_stop_at_nine(self):
        """Pure-oracle simulation should reach stop at count 9."""
        result = simulate_chain_oracle()
        
        self.assertTrue(result.stop_reached)
        self.assertEqual(result.final_counter_state.count, 9)
        self.assertEqual(result.final_counter_state.stop, 1)
    
    def test_counter_increments_on_hits(self):
        """Counter should increment each time hit_wall is detected."""
        result = simulate_chain_oracle()
        
        # Count how many times hit_wall was 1
        total_hits = sum(result.hit_wall_history)
        
        # Counter should equal total hits (up to 9)
        expected_count = min(total_hits, 9)
        self.assertEqual(result.final_counter_state.count, expected_count)
    
    def test_ball_freezes_at_stop(self):
        """Ball should freeze once stop is asserted."""
        result = simulate_chain_oracle()
        
        if result.freeze_tick is not None:
            # After freeze_tick, ball position should not change
            for i in range(result.freeze_tick + 1, len(result.states)):
                self.assertEqual(
                    result.states[i].physics_state.ball_x,
                    result.states[result.freeze_tick].physics_state.ball_x,
                )
                self.assertEqual(
                    result.states[i].physics_state.ball_y,
                    result.states[result.freeze_tick].physics_state.ball_y,
                )
    
    def test_stop_latched(self):
        """Once stop=1, it should remain 1."""
        result = simulate_chain_oracle()
        
        # Find when stop was first set
        stop_indices = [i for i, s in enumerate(result.stop_history) if s == 1]
        
        if stop_indices:
            first_stop = stop_indices[0]
            # All subsequent stops should be 1
            for s in result.stop_history[first_stop:]:
                self.assertEqual(s, 1)
    
    def test_full_simulation_has_frames(self):
        """Full simulation should produce frames."""
        result = simulate_chain_oracle()
        
        self.assertGreater(len(result.frames), 0)
        self.assertEqual(len(result.frames), len(result.frames_compact))
        self.assertEqual(len(result.frames), len(result.states))
    
    def test_custom_initial_state(self):
        """Simulation with custom initial state."""
        initial_physics = PhysicsState(ball_x=10, ball_y=10, vel_x=0, vel_y=1)
        initial_counter = CounterState(count=0, stop=0)
        
        result = simulate_chain(
            initial_physics=initial_physics,
            initial_counter=initial_counter,
            max_ticks=100,
        )
        
        self.assertEqual(result.final_physics_state.ball_x, 10)  # Should be moving down
        self.assertGreaterEqual(result.final_counter_state.count, 0)


class AcceptanceGateTests(unittest.TestCase):
    """
    Tests for D4 acceptance gates.
    
    Acceptance Gate 3: Pure-oracle integrated simulation reaches stop at count 9 and freezes motion.
    """
    
    def test_acceptance_gate_3_oracle(self):
        """
        Acceptance Gate 3: Pure-oracle integrated simulation (A -> B -> A) 
        reaches stop at count 9 and freezes motion.
        """
        result = simulate_chain_oracle()
        
        # Must reach stop
        self.assertTrue(result.stop_reached, "Stop was never reached")
        
        # Must reach exactly count 9
        self.assertEqual(
            result.final_counter_state.count, 9,
            f"Counter stopped at {result.final_counter_state.count} instead of 9"
        )
        
        # Stop bit must be 1
        self.assertEqual(
            result.final_counter_state.stop, 1,
            "Stop bit should be 1 when counter reaches 9"
        )
        
        # Ball should be frozen after stop
        if result.freeze_tick is not None and result.freeze_tick < len(result.states) - 1:
            for i in range(result.freeze_tick + 1, len(result.states)):
                self.assertEqual(
                    result.states[i].physics_state.ball_x,
                    result.states[result.freeze_tick].physics_state.ball_x,
                    f"Ball moved after freeze at tick {result.freeze_tick}"
                )
                self.assertEqual(
                    result.states[i].physics_state.ball_y,
                    result.states[result.freeze_tick].physics_state.ball_y,
                    f"Ball moved after freeze at tick {result.freeze_tick}"
                )
        
        print(f"\nAcceptance Gate 3 PASSED:")
        print(f"  Stop reached at tick {result.freeze_tick}")
        print(f"  Final count: {result.final_counter_state.count}")
        print(f"  Total wall hits: {sum(result.hit_wall_history)}")


if __name__ == "__main__":
    unittest.main()
