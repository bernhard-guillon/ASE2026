"""
Model inference and validation script.
Tests trained model with character predictions.
"""

import torch
import numpy as np
import json
from model import create_model


def load_model(model_path="model.pth", device='cpu'):
    """Load trained model from checkpoint."""
    model = create_model(device=device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    return model


def load_char_map(char_map_path="char_map.json"):
    """Load character mapping from JSON."""
    with open(char_map_path, 'r') as f:
        char_map = json.load(f)
    # Convert string keys back to integers
    return {int(k): v for k, v in char_map.items()}


def load_dataset(dataset_path="dataset.npz"):
    """Load dataset from numpy archive."""
    data = np.load(dataset_path)
    return data['x'], data['y']


def predict_character(model, image_array, char_map, device='cpu'):
    """
    Predict character from image array.
    
    Args:
        model: Trained PyTorch model
        image_array: Flattened 400-dimensional array
        char_map: Character index mapping
        device: 'cpu' or 'cuda'
    
    Returns:
        predicted_char: Character prediction
        confidence: Confidence score (0-1)
    """
    x_tensor = torch.FloatTensor(image_array).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(x_tensor)
        probs = torch.softmax(output, dim=1)
        confidence, pred_idx = torch.max(probs, 1)
    
    pred_char = char_map[pred_idx.item()]
    return pred_char, confidence.item()


def validate_model(model_path="model.pth", dataset_path="dataset.npz", 
                  char_map_path="char_map.json"):
    """Validate model and print accuracy metrics."""
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading model from {model_path} on device: {device}")
    
    # Load model, data, and character map
    model = load_model(model_path, device=device)
    x_data, y_data = load_dataset(dataset_path)
    char_map = load_char_map(char_map_path)
    
    # Convert to tensor
    x_tensor = torch.FloatTensor(x_data).to(device)
    y_tensor = torch.LongTensor(y_data).to(device)
    
    # Get predictions
    with torch.no_grad():
        outputs = model(x_tensor)
        probs = torch.softmax(outputs, dim=1)
        confidences, predictions = torch.max(probs, 1)
    
    predictions = predictions.cpu().numpy()
    confidences = confidences.cpu().numpy()
    
    # Calculate accuracy
    correct = (predictions == y_data).sum()
    total = len(y_data)
    accuracy = correct / total
    
    # Print results
    print("\n" + "=" * 60)
    print(f"MODEL VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total characters: {total}")
    print(f"Correct predictions: {correct}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Average confidence: {confidences.mean():.4f}")
    print("=" * 60)
    
    # Per-character results
    print("\nPer-Character Results:")
    print("-" * 60)
    errors = 0
    for idx in range(total):
        pred_char = char_map[predictions[idx]]
        true_char = char_map[y_data[idx]]
        confidence = confidences[idx]
        is_correct = predictions[idx] == y_data[idx]
        status = "✓" if is_correct else "✗"
        
        if not is_correct:
            errors += 1
        
        true_display = true_char if true_char != ' ' else 'SPACE'
        pred_display = pred_char if pred_char != ' ' else 'SPACE'
        
        print(f"{status} {idx:2d}: {true_display:5s} → {pred_display:5s} "
              f"(conf: {confidence:.4f})")
    
    print("-" * 60)
    if accuracy >= 0.80:
        print(f"✓ Validation PASSED (accuracy >= 80%)")
    else:
        print(f"✗ Validation FAILED (accuracy < 80%)")
    
    return accuracy


def interactive_predict(model_path="model.pth", 
                       char_map_path="char_map.json",
                       dataset_path="dataset.npz"):
    """Interactive character prediction from dataset."""
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = load_model(model_path, device=device)
    char_map = load_char_map(char_map_path)
    x_data, y_data = load_dataset(dataset_path)
    
    print("\n" + "=" * 60)
    print("INTERACTIVE PREDICTION")
    print("=" * 60)
    
    for idx in range(len(x_data)):
        pred_char, confidence = predict_character(
            model, x_data[idx], char_map, device
        )
        true_char = char_map[y_data[idx]]
        status = "✓" if pred_char == true_char else "✗"
        
        true_display = true_char if true_char != ' ' else 'SPACE'
        pred_display = pred_char if pred_char != ' ' else 'SPACE'
        
        print(f"{status} Char {idx:2d}: True={true_display:5s} "
              f"Pred={pred_display:5s} Conf={confidence:.4f}")


if __name__ == "__main__":
    print("PyTorch Character Recognition Model - Inference Script\n")
    
    # Validate the model
    accuracy = validate_model()
    
    # Run interactive predictions
    interactive_predict()
    
    print("\n" + "=" * 60)
    print("Inference complete!")
    print("=" * 60)
