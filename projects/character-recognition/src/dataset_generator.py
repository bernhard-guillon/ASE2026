"""
Generate character dataset for PyTorch training.
Renders alphanumeric characters as 20x20 grayscale pixel images.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os


def generate_character_dataset(output_path="dataset.npz"):
    """
    Generate training dataset from alphanumeric characters.
    
    Returns:
        - X: numpy array of shape (37, 400) - flattened 20x20 images
        - y: numpy array of shape (37,) - character class indices
        - char_map: dict mapping class indices to characters
    """
    # Character set: A-Z (26), 0-9 (10), space (1) = 37 total
    characters = [chr(i) for i in range(ord('A'), ord('Z') + 1)] + \
                 [str(i) for i in range(10)] + [' ']
    
    assert len(characters) == 37, f"Expected 37 characters, got {len(characters)}"
    
    img_size = 20
    x_data = []
    y_data = []
    char_map = {i: char for i, char in enumerate(characters)}
    
    # Try to use a monospace font
    font_size = 16
    try:
        # Try DejaVu monospace first
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
    except (FileNotFoundError, OSError):
        try:
            # Fallback to Liberation Mono
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", font_size)
        except (FileNotFoundError, OSError):
            # Use default font
            font = ImageFont.load_default()
    
    print(f"Generating dataset with {len(characters)} characters...")
    
    for class_idx, char in enumerate(characters):
        # Create blank image
        img = Image.new('L', (img_size, img_size), color=0)  # Black background
        draw = ImageDraw.Draw(img)
        
        # Draw character in white
        # Calculate position to center the character
        bbox = draw.textbbox((0, 0), char, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x_pos = (img_size - text_width) // 2
        y_pos = (img_size - text_height) // 2
        
        draw.text((x_pos, y_pos), char, fill=255, font=font)  # White text
        
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        # Flatten to 1D array (400 features)
        flattened = img_array.flatten()
        
        x_data.append(flattened)
        y_data.append(class_idx)
        
        # Save individual character image for debugging
        debug_dir = "debug_chars"
        os.makedirs(debug_dir, exist_ok=True)
        char_display = char if char != ' ' else 'space'
        img.save(f"{debug_dir}/{class_idx:02d}_{char_display}.png")
    
    x_data = np.array(x_data, dtype=np.float32)  # Shape: (37, 400)
    y_data = np.array(y_data, dtype=np.int64)    # Shape: (37,)
    
    # Save dataset
    np.savez(output_path, x=x_data, y=y_data)
    print(f"Dataset saved to {output_path}")
    print(f"  X shape: {x_data.shape}")
    print(f"  y shape: {y_data.shape}")
    print(f"Character mapping: {char_map}")
    
    return x_data, y_data, char_map


if __name__ == "__main__":
    generate_character_dataset()
