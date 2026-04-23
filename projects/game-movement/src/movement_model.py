"""
PyTorch model for deterministic single-player movement transitions on a 20x20 board.
Input: current board (400) + action one-hot (5) = 405.
Output: next board logits (400).
"""

import torch
import torch.nn as nn


class PlayerMovementNetwork(nn.Module):
    def __init__(self, input_size: int = 405, hidden_size: int = 128, output_size: int = 400):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        return self.fc3(x)


def create_movement_model(device: str = "cpu") -> PlayerMovementNetwork:
    model = PlayerMovementNetwork()
    model.to(device)
    return model
