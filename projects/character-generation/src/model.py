"""
PyTorch neural network for character generation.
Architecture: 255 inputs (one-hot ASCII) -> 256 hidden -> 256 hidden -> 400 outputs (20x20 pixel image)
"""

import torch
import torch.nn as nn


class CharacterGeneratorNetwork(nn.Module):
    """Neural network for generating character images from ASCII codes."""
    
    def __init__(self, input_size=255, hidden_size=256, output_size=400):
        """
        Args:
            input_size: Number of input features (255 for one-hot ASCII encoding)
            hidden_size: Number of hidden neurons
            output_size: Number of output features (20x20 = 400 pixels)
        """
        super(CharacterGeneratorNetwork, self).__init__()
        
        # Encoder: ASCII input -> hidden representation
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu1 = nn.ReLU()
        
        # Bottleneck layer
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu2 = nn.ReLU()
        
        # Decoder: hidden representation -> pixel image
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()  # Output in [0, 1] for pixel values
    
    def forward(self, x):
        """Forward pass through the network."""
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.fc3(x)
        x = self.sigmoid(x)  # Ensure output is in [0, 1] range
        return x


def create_model(device='cpu'):
    """Create and return the model."""
    model = CharacterGeneratorNetwork(input_size=255, hidden_size=256, output_size=400)
    model.to(device)
    return model


def get_optimizer(model, learning_rate=0.001):
    """Create optimizer for the model."""
    return torch.optim.Adam(model.parameters(), lr=learning_rate)


def get_loss_function():
    """Create loss function for image generation (MSE Loss)."""
    return nn.MSELoss()
