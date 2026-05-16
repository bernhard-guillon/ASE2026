#!/usr/bin/env python3
"""
Dual Model Game - Standalone demonstration of the two-model squash control chain.

This script runs the complete dual-model system:
- Model A (Physics): Ball movement with wall bounce
- Model B (Counter): Hit counter with stop at 9
- Deterministic renderer: Draws 20x20 grid with walls, ball, counter

Usage:
    python dual_model_game.py [--max-ticks N] [--oracle] [--ml]

Options:
    --max-ticks N: Maximum number of ticks to simulate (default: 500)
    --oracle: Use deterministic oracles (default)
    --ml: Use trained ML models (requires physics_model.pth and counter_model.pth)
    --animate: Print each frame with a delay
    --output-dir DIR: Save frames to directory
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

from dual_model_contract import PhysicsState, CounterState, default_physics_state, default_counter_state
from chain_integrator import simulate_chain, simulate_chain_oracle, save_simulation_animation
from deterministic_renderer import render_frame, print_frame
from physics_model import create_physics_model
from counter_model import create_counter_model


def load_ml_models(device: str = "cpu") -> tuple[torch.nn.Module, torch.nn.Module]:
    """Load trained ML models."""
    physics_path = Path("physics_model.pth")
    counter_path = Path("counter_model.pth")
    
    if not physics_path.exists():
        raise FileNotFoundError(f"Physics model not found: {physics_path}")
    if not counter_path.exists():
        raise FileNotFoundError(f"Counter model not found: {counter_path}")
    
    physics_model = create_physics_model(device=device)
    counter_model = create_counter_model(device=device)
    
    physics_checkpoint = torch.load(physics_path, map_location=device)
    counter_checkpoint = torch.load(counter_path, map_location=device)
    
    physics_model.load_state_dict(physics_checkpoint["model_state_dict"])
    counter_model.load_state_dict(counter_checkpoint["model_state_dict"])
    
    return physics_model, counter_model


def run_oracle_game(max_ticks: int = 500, output_dir: str = None, animate: bool = False) -> dict:
    """Run the game using deterministic oracles."""
    result = simulate_chain_oracle()
    
    if output_dir:
        save_simulation_animation(result, output_dir)
    
    if animate:
        for i, frame in enumerate(result.frames):
            print(f"\033[H\033[JTick {i}: count={result.states[i].counter_state.count}, "
                  f"stop={result.states[i].counter_state.stop}, "
                  f"hit_wall={result.states[i].hit_wall if i > 0 else 0}")
            print(frame)
            time.sleep(0.1)
    else:
        # Print summary frames
        print("Initial frame:")
        print(result.frames[0])
        print()
        
        if len(result.frames) > 1:
            print("Final frame:")
            print(result.frames[-1])
            print()
    
    return {
        "status": "success",
        "final_count": result.final_counter_state.count,
        "stop_reached": result.stop_reached,
        "freeze_tick": result.freeze_tick,
        "total_ticks": result.num_ticks,
        "total_hits": sum(result.hit_wall_history),
    }


def run_ml_game(max_ticks: int = 500, output_dir: str = None, animate: bool = False) -> dict:
    """Run the game using trained ML models."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        physics_model, counter_model = load_ml_models(device)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    
    from chain_integrator import simulate_chain_with_ml_models
    result = simulate_chain_with_ml_models(
        physics_model, counter_model, device=device, max_ticks=max_ticks
    )
    
    if output_dir:
        save_simulation_animation(result, output_dir)
    
    if animate:
        for i, frame in enumerate(result.frames):
            print(f"\033[H\033[JTick {i}: count={result.states[i].counter_state.count}")
            print(frame)
            time.sleep(0.1)
    else:
        print("Initial frame:")
        print(result.frames[0])
        print()
        print("Final frame:")
        print(result.frames[-1])
        print()
    
    return {
        "status": "success",
        "final_count": result.final_counter_state.count,
        "stop_reached": result.stop_reached,
        "freeze_tick": result.freeze_tick,
        "total_ticks": result.num_ticks,
        "total_hits": sum(result.hit_wall_history),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual Model Squash Control Chain Game")
    parser.add_argument("--max-ticks", type=int, default=500, help="Maximum ticks to simulate")
    parser.add_argument("--oracle", action="store_true", default=True, help="Use oracle (default)")
    parser.add_argument("--ml", action="store_true", help="Use trained ML models")
    parser.add_argument("--animate", action="store_true", help="Animate frames")
    parser.add_argument("--output-dir", type=str, default=None, help="Save frames to directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    
    if args.ml:
        args.oracle = False
    
    if args.animate and args.output_dir:
        print("Note: --animate and --output-dir are mutually exclusive for clean output")
        args.animate = False
    
    print("Dual Model Squash Control Chain Game")
    print("=" * 50)
    
    if args.oracle:
        print("Mode: Oracle (deterministic)")
        result = run_oracle_game(args.max_ticks, args.output_dir, args.animate)
    else:
        print("Mode: ML (trained models)")
        result = run_ml_game(args.max_ticks, args.output_dir, args.animate)
    
    print("=" * 50)
    print("Results:")
    if result["status"] == "success":
        print(f"  Final count: {result['final_count']}")
        print(f"  Stop reached: {result['stop_reached']}")
        print(f"  Freeze tick: {result['freeze_tick']}")
        print(f"  Total ticks: {result['total_ticks']}")
        print(f"  Total wall hits: {result['total_hits']}")
        
        if result['stop_reached'] and result['final_count'] == 9:
            print("\n✓ D5 Acceptance Gate PASSED: Count 0->9, stop asserted, ball frozen")
            return 0
        else:
            print("\n✗ D5 Acceptance Gate FAILED")
            return 1
    else:
        print(f"  Error: {result.get('message', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
