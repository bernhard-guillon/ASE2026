"""
Simple PyTorch neural network for character recognition.
Architecture: 400 inputs -> 128 hidden -> 37 output classes
"""

import torch
import torch.nn as nn


class CharacterNetwork(nn.Module):
    """Simple 2-layer neural network for character classification."""
    
    def __init__(self, input_size=400, hidden_size=128, output_size=37):
        """
        Args:
            input_size: Number of input features (20x20 = 400)
            hidden_size: Number of hidden neurons
            output_size: Number of output classes (37 characters)
        """
        super(CharacterNetwork, self).__init__()
        
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        """Forward pass through the network."""
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


def create_model(device='cpu'):
    """Create and return the model."""
    model = CharacterNetwork(input_size=400, hidden_size=128, output_size=37)
    model.to(device)
    return model


def get_optimizer(model, learning_rate=0.001):
    """Create optimizer for the model."""
    return torch.optim.Adam(model.parameters(), lr=learning_rate)


def get_loss_function():
    """Create loss function for multi-class classification."""
    return nn.CrossEntropyLoss()
