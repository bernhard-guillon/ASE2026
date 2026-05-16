"""
Chained Model for Dual-Model Squash Control Chain.

This model contains BOTH the physics model and counter model as separate,
disconnected sub-networks. Only the explicit control signals (hit_wall, stop)
are wired between them.

Architecture:
    Input: compact state encoding
        - physics_state: 46 elements (ball_x one-hot 20 + ball_y one-hot 20 + vel_x 3 + vel_y 3)
        - counter_state: 11 elements (count one-hot 10 + stop 1)
        - Total input: 46 + 11 = 57 elements
    
    Internal:
        - Physics sub-network (47 -> 47): takes physics_state + stop_bit
        - Counter sub-network (12 -> 11): takes counter_state + hit_wall
        - Wiring: physics hit_wall output -> counter hit_wall input
        - Wiring: counter stop output -> physics stop input
    
    Output: compact state encoding
        - next_physics_state: 46 elements
        - next_counter_state: 11 elements
        - Total output: 46 + 11 = 57 elements

This maintains the two-model separation as specified in the handoff document.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from dual_model_contract import (
    GRID_SIZE,
    PhysicsState,
    CounterState,
    encode_physics_state,
    encode_counter_state,
    decode_physics_state,
    decode_counter_state,
    physics_step_input,
    counter_step_input,
)
from physics_model import PhysicsNetwork, PHYSICS_INPUT_SIZE, PHYSICS_OUTPUT_SIZE
from counter_model import CounterNetwork, COUNTER_INPUT_SIZE, COUNTER_OUTPUT_SIZE


# Chained model dimensions
# Input: physics_state (46) + counter_state (11) = 57
CHAINED_INPUT_SIZE = GRID_SIZE + GRID_SIZE + 3 + 3 + 10 + 1
# Output: next_physics_state (46) + next_counter_state (11) = 57
CHAINED_OUTPUT_SIZE = GRID_SIZE + GRID_SIZE + 3 + 3 + 10 + 1


class ChainedModel(nn.Module):
    """
    Chained model containing both physics and counter sub-networks.
    
    The two sub-networks operate independently with only the explicit
    control bits (hit_wall, stop) connecting them.
    
    Input: 57 elements (encoded physics state + encoded counter state)
    Output: 57 elements (encoded next physics state + encoded next counter state)
    """
    
    def __init__(
        self,
        physics_model: PhysicsNetwork = None,
        counter_model: CounterNetwork = None,
    ):
        super().__init__()
        
        # Create sub-networks
        self.physics = physics_model if physics_model else PhysicsNetwork()
        self.counter = counter_model if counter_model else CounterNetwork()
        
        # Freeze sub-networks (they are pre-trained)
        for param in self.physics.parameters():
            param.requires_grad = False
        for param in self.counter.parameters():
            param.requires_grad = False
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the chained model.
        
        Args:
            x: Input tensor of shape (batch, 57)
                - Elements 0-45: encoded physics state (ball_x, ball_y, vel_x, vel_y)
                - Elements 46-56: encoded counter state (count one-hot 10 + stop 1)
        
        Returns:
            Output tensor of shape (batch, 57)
                - Elements 0-45: encoded next physics state
                - Elements 46-56: encoded next counter state
        """
        # Split input
        physics_state_enc = x[:, :46]       # (batch, 46)
        counter_state_enc = x[:, 46:57]     # (batch, 11)
        
        # Extract stop bit from counter state encoding (last element of counter state)
        stop_bit = counter_state_enc[:, -1:]  # (batch, 1)
        
        # Build physics input: physics_state + stop_bit
        physics_input = torch.cat([physics_state_enc, stop_bit], dim=1)  # (batch, 47)
        
        # Run physics sub-network
        physics_output = self.physics(physics_input)  # (batch, 47)
        
        # Extract hit_wall (last element of physics output)
        hit_wall = physics_output[:, -1:]  # (batch, 1)
        
        # Extract next physics state (first 46 elements)
        next_physics_state_enc = physics_output[:, :46]  # (batch, 46)
        
        # Build counter input: counter_state + hit_wall
        counter_input = torch.cat([counter_state_enc, hit_wall], dim=1)  # (batch, 12)
        
        # Run counter sub-network
        counter_output = self.counter(counter_input)  # (batch, 11)
        
        # Combine outputs
        output = torch.cat([next_physics_state_enc, counter_output], dim=1)  # (batch, 57)
        
        return output
    
    def step(self, physics_state: PhysicsState, counter_state: CounterState) -> tuple[PhysicsState, CounterState]:
        """
        Perform a single chained step using the model.
        
        Args:
            physics_state: Current physics state
            counter_state: Current counter state
        
        Returns:
            Tuple of (next_physics_state, next_counter_state)
        """
        self.eval()
        with torch.no_grad():
            # Encode states
            physics_enc = encode_physics_state(physics_state)
            counter_enc = encode_counter_state(counter_state)
            
            # Build input
            input_vec = torch.cat([
                torch.tensor(physics_enc, dtype=torch.float32),
                torch.tensor(counter_enc, dtype=torch.float32),
            ]).unsqueeze(0)
            
            # Forward
            output_vec = self.forward(input_vec).squeeze(0).numpy()
        
        # Decode outputs
        next_physics_enc = output_vec[:46]
        next_counter_enc = output_vec[46:57]
        
        next_physics_state = decode_physics_state(next_physics_enc)
        next_counter_state = decode_counter_state(next_counter_enc)
        
        return next_physics_state, next_counter_state


def create_chained_model(
    physics_checkpoint: str = None,
    counter_checkpoint: str = None,
    device: str = "cpu",
) -> ChainedModel:
    """
    Create a chained model, optionally loading pre-trained weights.
    
    Args:
        physics_checkpoint: Path to physics model checkpoint
        counter_checkpoint: Path to counter model checkpoint
        device: Device to place model on
    
    Returns:
        ChainedModel with loaded weights
    """
    physics_model = PhysicsNetwork()
    counter_model = CounterNetwork()
    
    if physics_checkpoint:
        checkpoint = torch.load(physics_checkpoint, map_location=device)
        physics_model.load_state_dict(checkpoint.get("model_state_dict", checkpoint))
    
    if counter_checkpoint:
        checkpoint = torch.load(counter_checkpoint, map_location=device)
        counter_model.load_state_dict(checkpoint.get("model_state_dict", checkpoint))
    
    model = ChainedModel(physics_model, counter_model)
    model.to(device)
    return model
