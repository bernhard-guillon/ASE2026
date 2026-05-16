"""
Combined Model for Dual-Model Squash Control Chain.

This is a single neural network model that implements the combined behavior of:
- Model A (Physics): Ball movement with wall bounce
- Model B (Counter): Hit counter with stop at 9

The model takes a framebuffer (20x20 = 400 cells) as input and outputs the next
framebuffer. This maintains compatibility with the emulator's expected interface.

However, the RECOMMENDED approach (per handoff doc) is to keep the two-model
separation and use a deterministic renderer. This combined model is provided for
emulator integration (Option 4a) where a single model interface is required.

Architecture:
- Input: 400 (framebuffer cells, normalized 0-1)
- Hidden layers: 256, 256, 256 with ReLU
- Output: 400 (next framebuffer cells)
"""

from __future__ import annotations

import torch
import torch.nn as nn


class CombinedModel(nn.Module):
    """
    Combined neural network for the full dual-model squash game.
    
    Input: 400 normalized pixel values (0-1)
    Output: 400 pixel values for next frame
    """
    
    def __init__(
        self,
        input_size: int = 400,
        hidden_size: int = 256,
        output_size: int = 400,
    ):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size, hidden_size)
        self.relu3 = nn.ReLU()
        self.fc4 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.fc3(x)
        x = self.relu3(x)
        return self.fc4(x)


def create_combined_model(device: str = "cpu") -> CombinedModel:
    """Factory function to create and place combined model on device."""
    model = CombinedModel()
    model.to(device)
    return model
