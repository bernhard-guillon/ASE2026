"""
PyTorch model for Model A (Physics Model).

Predicts next physics state + hit_wall bit from current physics state + stop bit.

Input: encoded physics state (46) + stop bit (1) = 47 elements
Output: encoded next physics state (46) + hit_wall bit (1) = 47 elements

Architecture:
- 3 hidden layers with ReLU activation
- Output is logits for each dimension (categorical for one-hot encoded parts)
"""

from __future__ import annotations

import torch
import torch.nn as nn

from dual_model_contract import GRID_SIZE


# Input size: 20 (ball_x one-hot) + 20 (ball_y one-hot) + 3 (vel_x one-hot) + 3 (vel_y one-hot) + 1 (stop bit) = 47
PHYSICS_INPUT_SIZE = GRID_SIZE + GRID_SIZE + 3 + 3 + 1
# Output size: same as input (next state encoding + hit_wall) = 47
PHYSICS_OUTPUT_SIZE = GRID_SIZE + GRID_SIZE + 3 + 3 + 1


class PhysicsNetwork(nn.Module):
    """
    Neural network for physics state transition prediction.
    
    Predicts:
    - next ball_x (20 one-hot buckets)
    - next ball_y (20 one-hot buckets)
    - next vel_x (3 one-hot buckets: -1, 0, 1)
    - next vel_y (3 one-hot buckets: -1, 0, 1)
    - hit_wall (1 bit: 0 or 1)
    """
    
    def __init__(
        self,
        input_size: int = PHYSICS_INPUT_SIZE,
        hidden_size: int = 128,
        output_size: int = PHYSICS_OUTPUT_SIZE,
    ):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        return self.fc3(x)


def create_physics_model(device: str = "cpu") -> PhysicsNetwork:
    """Factory function to create and place physics model on device."""
    model = PhysicsNetwork()
    model.to(device)
    return model
