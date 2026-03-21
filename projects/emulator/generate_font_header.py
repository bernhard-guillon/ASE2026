#!/usr/bin/env python3
"""
Generate character_font.h from the character-generation dataset.

Extracts the 255 pre-computed character images from dataset.npz and converts
them to a static C array. Pixel values in [0.0, 1.0] are converted to [0, 255]:
- pixel > 0.5: 255 (white/on)
- pixel <= 0.5: 0 (black/off)
"""

import numpy as np
import sys
from pathlib import Path

def generate_font_header(dataset_path, output_path):
    """Load dataset.npz and generate character_font.h"""
    
    # Load dataset
    print(f"Loading {dataset_path}...")
    data = np.load(dataset_path)
    y_data = data['y']  # Shape: (255, 400)
    
    if y_data.shape != (255, 400):
        raise ValueError(f"Expected y shape (255, 400), got {y_data.shape}")
    
    # Convert float32 [0.0, 1.0] to uint8 [0, 255]
    # Threshold: > 0.5 = 255 (on), <= 0.5 = 0 (off)
    char_images = np.where(y_data > 0.5, 255, 0).astype(np.uint8)
    
    print(f"Converted {char_images.shape[0]} characters, {char_images.shape[1]} pixels each")
    
    # Generate C header file
    with open(output_path, 'w') as f:
        f.write('/* Auto-generated character font header from dataset.npz */\n')
        f.write('/* 255 ASCII characters (0-254), each 20x20 pixels (400 bytes) */\n')
        f.write('/* Pixel threshold: > 0.5 = 255 (on), <= 0.5 = 0 (off) */\n\n')
        f.write('#ifndef CHARACTER_FONT_H\n')
        f.write('#define CHARACTER_FONT_H\n\n')
        f.write('#include <stdint.h>\n\n')
        
        # Static array declaration
        f.write('static const uint8_t char_images[255][400] = {\n')
        
        for char_idx in range(255):
            pixels = char_images[char_idx]
            
            # Format pixels in groups of 20 (one row per line)
            f.write(f'    {{ /* Character {char_idx:3d} */\n')
            for row in range(20):
                row_pixels = pixels[row * 20:(row + 1) * 20]
                f.write('        ')
                f.write(', '.join(f'{p:3d}' for p in row_pixels))
                if row < 19:
                    f.write(',\n')
                else:
                    f.write('\n')
            
            if char_idx < 254:
                f.write('    },\n')
            else:
                f.write('    }\n')
        
        f.write('};\n\n')
        f.write('#endif /* CHARACTER_FONT_H */\n')
    
    print(f"Generated {output_path}")

if __name__ == '__main__':
    # Default paths
    char_gen_dir = Path(__file__).parent.parent / 'character-generation'
    dataset_path = char_gen_dir / 'dataset.npz'
    output_path = Path(__file__).parent / 'character_font.h'
    
    if not dataset_path.exists():
        print(f"Error: {dataset_path} not found", file=sys.stderr)
        sys.exit(1)
    
    generate_font_header(dataset_path, output_path)
    print(f"✓ Font header generated successfully")
