"""
PyTorch model for Model B (Counter Model).

Predicts next counter state from current counter state + hit_wall bit.

Input: encoded counter state (11) + hit_wall bit (1) = 12 elements
Output: encoded next counter state (11 elements)

Architecture:
- 2-3 hidden layers with ReLU activation
- Output is logits for count (10 one-hot buckets) and stop bit (1 sigmoid)
"""

from __future__ import annotations

import torch
import torch.nn as nn


# Input size: 10 (count one-hot) + 1 (stop bit) + 1 (hit_wall) = 12
COUNTER_INPUT_SIZE = 10 + 1 + 1
# Output size: 10 (count one-hot) + 1 (stop bit) = 11
COUNTER_OUTPUT_SIZE = 10 + 1


class CounterNetwork(nn.Module):
    """
    Neural network for counter state transition prediction.
    
    Predicts:
    - next count (10 one-hot buckets: 0-9)
    - next stop (1 bit: 0 or 1)
    """
    
    def __init__(
        self,
        input_size: int = COUNTER_INPUT_SIZE,
        hidden_size: int = 64,
        output_size: int = COUNTER_OUTPUT_SIZE,
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


def create_counter_model(device: str = "cpu") -> CounterNetwork:
    """Factory function to create and place counter model on device."""
    model = CounterNetwork()
    model.to(device)
    return model
