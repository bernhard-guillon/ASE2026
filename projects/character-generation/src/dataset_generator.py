"""
Generate character generation dataset for PyTorch training.
Creates training pairs: ASCII character index (0-255) -> 20x20 pixel image (400 features)
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def generate_character_generation_dataset(output_path="dataset.npz"):
    """
    Generate training dataset for character generation.
    Maps ASCII character codes (0-255) to 20x20 pixel renderings.
    
    Returns:
        - X: numpy array of shape (255, 400) - character codes as input
        - y: numpy array of shape (255, 400) - flattened 20x20 images as output
        - char_map: dict mapping character codes to characters (for printing)
    """
    img_size = 20
    x_data = []
    y_data = []
    char_map = {}
    
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
    
    print(f"Generating character generation dataset for 255 ASCII characters...")
    
    # Generate dataset for ASCII characters 0-254 (255 total characters)
    # We use 0-254 to have 255 unique classes (0-indexed)
    debug_dir = "debug_chars"
    os.makedirs(debug_dir, exist_ok=True)
    
    for ascii_code in range(255):
        try:
            # Try to convert ASCII code to character
            char = chr(ascii_code)
            # Skip control characters (0-31) and DEL (127) - render as placeholder
            if ascii_code < 32 or ascii_code == 127:
                char = f'\\x{ascii_code:02x}'  # Show as hex representation
        except:
            char = '?'
        
        char_map[ascii_code] = char
        
        # Create input: one-hot encoded character code (simplified: just the code itself)
        # We'll use ASCII code directly as input feature
        input_code = np.zeros(255, dtype=np.float32)
        input_code[ascii_code] = 1.0  # One-hot encoding
        
        # Create blank image
        img = Image.new('L', (img_size, img_size), color=0)  # Black background
        draw = ImageDraw.Draw(img)
        
        # Draw character in white
        # Calculate position to center the character
        try:
            bbox = draw.textbbox((0, 0), char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x_pos = (img_size - text_width) // 2
            y_pos = (img_size - text_height) // 2
            draw.text((x_pos, y_pos), char, fill=255, font=font)  # White text
        except:
            # If character can't be rendered, draw a simple placeholder
            draw.rectangle([2, 2, img_size-2, img_size-2], outline=255)
        
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        # Flatten to 1D array (400 features - output)
        flattened = img_array.flatten()
        
        x_data.append(input_code)
        y_data.append(flattened)
        
        # Save individual character image for debugging (sample every 10)
        if ascii_code % 10 == 0:
            char_display = char if (32 <= ascii_code < 127) else f'{ascii_code}'
            img.save(f"{debug_dir}/{ascii_code:03d}_{char_display}.png")
    
    x_data = np.array(x_data, dtype=np.float32)  # Shape: (255, 255)
    y_data = np.array(y_data, dtype=np.float32)  # Shape: (255, 400)
    
    # Save dataset
    np.savez(output_path, x=x_data, y=y_data)
    print(f"Dataset saved to {output_path}")
    print(f"  Input shape: {x_data.shape} (255 ASCII codes, one-hot encoded)")
    print(f"  Output shape: {y_data.shape} (255 ASCII codes → 20x20 pixel images)")
    
    return x_data, y_data, char_map