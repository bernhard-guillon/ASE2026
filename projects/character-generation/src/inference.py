"""
Model inference and validation script for character generation.
Tests trained model with character image generation from ASCII codes.
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


def generate_character_image(model, ascii_code, device='cpu'):
    """
    Generate a 20x20 pixel image from an ASCII code.

    Args:
        model: Trained PyTorch character generation model
        ascii_code: Integer ASCII code (0-254)
        device: 'cpu' or 'cuda'

    Returns:
        image_array: 400-dimensional flattened pixel array (values in [0, 1])
    """
    input_code = np.zeros(255, dtype=np.float32)
    input_code[ascii_code] = 1.0  # One-hot encoding

    x_tensor = torch.FloatTensor(input_code).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(x_tensor)

    return output.squeeze(0).cpu().numpy()


def print_character_image(image_array, title="Generated Character"):
    """Print a 20x20 character image as ASCII art to the console."""
    pixels = image_array.reshape(20, 20)
    print(f"\n{title}:")
    for row in pixels:
        line = "".join("█" if p > 0.5 else " " for p in row)
        print(f"  |{line}|")


def validate_model(model_path="model.pth", dataset_path="dataset.npz",
                   char_map_path="char_map.json"):
    """Validate model and print MSE metrics for all characters."""

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading model from {model_path} on device: {device}")

    # Load model, data, and character map
    model = load_model(model_path, device=device)
    x_data, y_data = load_dataset(dataset_path)
    char_map = load_char_map(char_map_path)

    # Convert to tensors
    x_tensor = torch.FloatTensor(x_data).to(device)
    y_tensor = torch.FloatTensor(y_data).to(device)

    # Get predictions
    with torch.no_grad():
        outputs = model(x_tensor)
        overall_mse = torch.nn.MSELoss()(outputs, y_tensor).item()

    outputs_np = outputs.cpu().numpy()

    # Print results
    print("\n" + "=" * 60)
    print("MODEL VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total characters: {len(x_data)}")
    print(f"Overall MSE Loss: {overall_mse:.6f}")
    print("=" * 60)

    # Per-character MSE
    print("\nPer-Character MSE (sample of 20):")
    print("-" * 60)
    sample_indices = list(range(0, 255, 13))[:20]  # Sample ~20 characters
    for idx in sample_indices:
        generated = outputs_np[idx]
        target = y_data[idx]
        mse = np.mean((generated - target) ** 2)
        char = char_map.get(idx, f'\\x{idx:02x}')
        char_display = char if (32 <= idx < 127 and char != ' ') else f'ASCII {idx}'
        print(f"  {char_display:12s}: MSE = {mse:.6f}")

    print("-" * 60)
    if overall_mse <= 0.05:
        print(f"✓ Validation PASSED (MSE <= 0.05)")
    else:
        print(f"✗ Validation FAILED (MSE > 0.05)")

    return overall_mse


def interactive_generate(model_path="model.pth",
                         char_map_path="char_map.json"):
    """Interactively generate character images from ASCII codes."""

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = load_model(model_path, device=device)
    char_map = load_char_map(char_map_path)

    print("\n" + "=" * 60)
    print("INTERACTIVE CHARACTER GENERATION")
    print("=" * 60)

    # Generate a selection of printable ASCII characters
    sample_codes = [ord(c) for c in "AaBb0 !"]
    for ascii_code in sample_codes:
        if ascii_code >= 255:
            continue
        image = generate_character_image(model, ascii_code, device)
        char = char_map.get(ascii_code, f'\\x{ascii_code:02x}')
        char_display = char if char.strip() else 'SPACE'
        print_character_image(image, title=f"ASCII {ascii_code} ({char_display})")


if __name__ == "__main__":
    print("PyTorch Character Generation Model - Inference Script\n")

    # Validate the model
    mse = validate_model()

    # Run interactive generation
    interactive_generate()

    print("\n" + "=" * 60)
    print("Inference complete!")
    print("=" * 60)
