"""
Main training script for character recognition model.
Generates dataset, trains model, and saves results.
"""

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import json
import sys

from dataset_generator import generate_character_dataset
from model import create_model, get_optimizer, get_loss_function


def train_model(
    x_data, y_data, char_map,
    epochs=100,
    batch_size=8,
    learning_rate=0.001,
    device='cpu'
):
    """
    Train the character recognition model.
    
    Args:
        x_data: Input features (37, 400)
        y_data: Target labels (37,)
        char_map: Character to index mapping
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
    y_tensor = torch.LongTensor(y_data).to(device)
    
    # Create dataset and dataloader
    dataset = TensorDataset(x_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Create model, optimizer, loss function
    model = create_model(device=device)
    optimizer = get_optimizer(model, learning_rate=learning_rate)
    criterion = get_loss_function()
    
    # Training loop
    print(f"Training for {epochs} epochs on {device}...")
    metrics = {
        'epochs': [],
        'train_loss': [],
        'accuracy': []
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
            _, predictions = torch.max(outputs, 1)
            accuracy = (predictions == y_tensor).float().mean().item()
        
        avg_loss = epoch_loss / len(dataloader)
        metrics['epochs'].append(epoch + 1)
        metrics['train_loss'].append(avg_loss)
        metrics['accuracy'].append(accuracy)
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}")
    
    print(f"Training complete!")
    print(f"Final Accuracy: {metrics['accuracy'][-1]:.4f}")
    
    return model, metrics


def evaluate_model(model, x_data, y_data, char_map, device='cpu'):
    """Evaluate model and print per-character accuracy."""
    x_tensor = torch.FloatTensor(x_data).to(device)
    y_tensor = torch.LongTensor(y_data).to(device)
    
    model.eval()
    with torch.no_grad():
        outputs = model(x_tensor)
        _, predictions = torch.max(outputs, 1)
    
    # Print per-character results
    print("\nPer-Character Predictions:")
    print("-" * 40)
    for idx, (pred, true) in enumerate(zip(predictions.cpu().numpy(), y_data)):
        char = char_map[idx]
        char_display = char if char != ' ' else 'SPACE'
        status = "✓" if pred == true else "✗"
        print(f"{status} {idx:2d}: {char_display:5s} - Predicted: {char_map[pred]}")
    
    overall_accuracy = (predictions == y_tensor).float().mean().item()
    print(f"\nOverall Accuracy: {overall_accuracy:.4f}")
    return overall_accuracy


def save_model(model, filepath="model.pth"):
    """Save trained model."""
    torch.save(model.state_dict(), filepath)
    print(f"Model saved to {filepath}")


def main():
    # Detect device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    # Generate dataset
    print("\n=== Generating Dataset ===")
    x_data, y_data, char_map = generate_character_dataset("dataset.npz")
    
    # Train model
    print("\n=== Training Model ===")
    model, metrics = train_model(
        x_data, y_data, char_map,
        epochs=150,
        batch_size=8,
        learning_rate=0.001,
        device=device
    )
    
    # Evaluate model
    print("\n=== Evaluating Model ===")
    accuracy = evaluate_model(model, x_data, y_data, char_map, device=device)
    
    # Save model and metrics
    print("\n=== Saving Results ===")
    save_model(model, "model.pth")
    
    # Save metrics to JSON
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("Metrics saved to metrics.json")
    
    # Save character map
    with open("char_map.json", "w") as f:
        # Convert int keys to strings for JSON
        char_map_str = {str(k): v for k, v in char_map.items()}
        json.dump(char_map_str, f, indent=2)
    print("Character map saved to char_map.json")
    
    print("\n=== Training Complete ===")
    print(f"Final Accuracy: {accuracy:.4f}")
    
    return model, metrics, accuracy


if __name__ == "__main__":
    main()
