"""
Main training script for character generation model.
Generates dataset, trains model, and saves results.
"""

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import json
import sys
import numpy as np

from dataset_generator import generate_character_generation_dataset
from model import create_model, get_optimizer, get_loss_function

def train_model(
    x_data, y_data,
    epochs=100,
    batch_size=8,
    learning_rate=0.001,
    device='cpu'
):
    """
    Train the character generation model.
    
    Args:
        x_data: Input features (255, 255) - one-hot encoded ASCII codes
        y_data: Target images (255, 400) - flattened 20x20 pixel images
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for optimizer
        device: 'cpu' or 'cuda'
    
    Returns:
        model: Trained model
        metrics: Training metrics
    """
    # Convert to tensors
    x_tensor = torch.FloatTensor(x_data).to(device)
    y_tensor = torch.FloatTensor(y_data).to(device)
    
    # Create dataset and dataloader
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Create model, optimizer, loss function
    model = create_model(device=device)
    optimizer = get_optimizer(model, learning_rate=learning_rate)
    criterion = get_loss_function()
    
    # Training loop
    print(f"Training for {epochs} epochs on {device}...")
    print(f"Model: 255 inputs -> 256 -> 256 -> 400 outputs")
    metrics = {
        'epochs': [],
        'train_loss': [],
        'validation_loss': []
    }
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        model.train()
        
        for batch_x, batch_y in dataloader:
            # Forward pass
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
        
        # Evaluation on all data
        model.eval()
        with torch.no_grad():
            outputs = model(x_tensor)
            val_loss = criterion(outputs, y_tensor).item()
        
        avg_loss = epoch_loss / len(dataloader)
        metrics['epochs'].append(epoch + 1)
        metrics['train_loss'].append(avg_loss)
        metrics['validation_loss'].append(val_loss)
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_loss:.6f}, Val Loss: {val_loss:.6f}")
    
    print(f"Training complete!")
    print(f"Final Training Loss: {metrics['train_loss'][-1]:.6f}")
    print(f"Final Validation Loss: {metrics['validation_loss'][-1]:.6f}")
    
    return model, metrics

def evaluate_model(model, x_data, y_data, device='cpu'):
    """Evaluate model and print sample outputs."""
    x_tensor = torch.FloatTensor(x_data).to(device)
    y_tensor = torch.FloatTensor(y_data).to(device)
    
    model.eval()
    with torch.no_grad():
        outputs = model(x_tensor)
        loss = nn.MSELoss()(outputs, y_tensor)
    
    print("\nModel Evaluation:")
    print("-" * 40)
    print(f"Validation MSE Loss: {loss.item():.6f}")
    
    # Print sample predictions
    print("\nSample Generated Images (MSE to target):")
    for idx in [0, 65, 97, 127, 254]:  # Sample ASCII codes
        if idx < len(x_data):
            sample_loss = nn.MSELoss()(outputs[idx], y_tensor[idx]).item()
            try:
                char = chr(idx)
            except:
                char = f'\\x{idx:02x}'
            print(f"  ASCII {idx} ({char}): MSE = {sample_loss:.6f}")

if __name__ == "__main__":
    # Setup device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")

    # Allow overriding hyperparameters via environment variables
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    # Generate dataset
    print("\n1. Generating dataset...")
    x_data, y_data, char_map = generate_character_generation_dataset("dataset.npz")

    # Train model
    print("\n2. Training model...")
    model, metrics = train_model(
        x_data, y_data,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=0.001,
        device=device
    )
    
    # Evaluate model
    print("\n3. Evaluating model...")
    evaluate_model(model, x_data, y_data, device=device)
    
    # Save model
    print("\n4. Saving model...")
    torch.save(model.state_dict(), "model.pth")
    print("Model saved to model.pth")
    
    # Save metrics
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("Metrics saved to metrics.json")
    
    # Save character map
    char_map_serializable = {str(k): v for k, v in char_map.items()}
    with open("char_map.json", "w") as f:
        json.dump(char_map_serializable, f, indent=2)
    print("Character map saved to char_map.json")
    
    print("\nTraining pipeline complete!")
