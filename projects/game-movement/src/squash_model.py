"""
Model for squash world-frame prediction:
current framebuffer + key input -> next framebuffer.
"""

import torch
import torch.nn as nn


class SquashWorldModel(nn.Module):
    def __init__(self, input_size: int = 655, hidden_size: int = 512, output_size: int = 400):
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


def create_squash_model(device: str = "cpu") -> SquashWorldModel:
    model = SquashWorldModel()
    model.to(device)
    return model
