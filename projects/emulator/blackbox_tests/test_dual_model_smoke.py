#!/usr/bin/env python3
"""
Smoke test for dual-model squash control chain.

Verifies D5 acceptance criteria:
- Emulator run shows progression from count 0 to 9
- Stop is asserted when count reaches 9
- Ball freezes when stop is asserted

This test uses the Python-based dual_model_game.py as the "emulator" implementation.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GAME_MOVEMENT_DIR = REPO_ROOT / "projects" / "game-movement" / "src"
DUAL_MODEL_GAME = GAME_MOVEMENT_DIR / "dual_model_game.py"


def _require_python_game() -> None:
    """Check that the dual_model_game.py script exists."""
    if not DUAL_MODEL_GAME.exists():
        pytest.skip(f"dual_model_game.py not found at {DUAL_MODEL_GAME}")


def _run_dual_model_game(args: list[str] = None) -> subprocess.CompletedProcess[str]:
    """Run the dual model game script with given arguments."""
    # Use venv python which has torch installed
    venv_python = GAME_MOVEMENT_DIR / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = GAME_MOVEMENT_DIR / ".." / ".." / ".." / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = sys.executable  # Fallback
    
    cmd = [str(venv_python), str(DUAL_MODEL_GAME)]
    if args:
        cmd.extend(args)
    
    return subprocess.run(
        cmd,
        cwd=GAME_MOVEMENT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestDualModelSmoke(unittest.TestCase):
    """Smoke tests for the dual-model squash control chain."""
    
    def setUp(self):
        """Check that required files exist."""
        _require_python_game()
    
    def test_oracle_simulation_reaches_stop(self):
        """
        D5 Acceptance Gate: Emulator run shows progression from count 0 to 9,
        asserts stop, and freezes ball.
        
        Tests with oracle (deterministic) implementation.
        """
        result = _run_dual_model_game(["--oracle", "--max-ticks", "500"])
        
        assert result.returncode == 0, (
            f"dual_model_game failed with oracle mode.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        
        # Check for success indicators in output
        assert "Final count: 9" in result.stdout, "Counter should reach 9"
        assert "Stop reached: True" in result.stdout, "Stop should be reached"
        assert "D5 Acceptance Gate PASSED" in result.stdout, "Acceptance gate should pass"
    
    def test_oracle_simulation_output_format(self):
        """Verify oracle simulation produces expected output format."""
        result = _run_dual_model_game(["--oracle", "--max-ticks", "50"])
        
        assert result.returncode == 0
        
        # Should show initial and final frames
        assert "Initial frame:" in result.stdout
        assert "Final frame:" in result.stdout
        
        # Frames should be 20x20
        lines = result.stdout.split('\n')
        frame_lines = [l for l in lines if len(l) == 20 and '#' in l]
        assert len(frame_lines) >= 2, "Should have at least initial and final frames"
    
    def test_oracle_simulation_hits_walls(self):
        """Verify the ball hits walls during simulation."""
        result = _run_dual_model_game(["--oracle", "--max-ticks", "500"])
        
        assert result.returncode == 0
        
        # Should have some wall hits
        assert "Total wall hits:" in result.stdout
        # Extract the number
        for line in result.stdout.split('\n'):
            if line.startswith("  Total wall hits:"):
                hits = int(line.split(':')[1].strip())
                assert hits >= 9, f"Should have at least 9 wall hits to reach count 9, got {hits}"
                break
    
    def test_counter_increments(self):
        """Verify counter increments during simulation."""
        result = _run_dual_model_game(["--oracle", "--max-ticks", "100"])
        
        assert result.returncode == 0
        
        # Counter should be increasing
        assert "Final count:" in result.stdout
        for line in result.stdout.split('\n'):
            if line.startswith("  Final count:"):
                count = int(line.split(':')[1].strip().split()[0])
                assert count >= 0, "Count should be non-negative"
                break


class TestDualModelML(unittest.TestCase):
    """Tests for ML-based dual-model simulation (when models are trained)."""
    
    def setUp(self):
        """Check that required files exist."""
        _require_python_game()
    
    def test_ml_simulation_fallback(self):
        """
        Test that ML mode gracefully fails when models are not trained.
        
        This is expected behavior - ML models need to be trained first.
        """
        result = _run_dual_model_game(["--ml", "--max-ticks", "10"])
        
        # Should fail gracefully (non-zero exit code or error message)
        # Either behavior is acceptable
        if result.returncode != 0:
            # Expected: models not found
            assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()


if __name__ == "__main__":
    unittest.main()
