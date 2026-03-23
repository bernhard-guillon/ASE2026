import torch
import torch.nn as nn
import numpy as np
import json

# Define the model architecture (3 layers, 255 input)
class CharacterGenerator(nn.Module):
    def __init__(self):
        super(CharacterGenerator, self).__init__()
        self.fc1 = nn.Linear(255, 256)
        self.fc2 = nn.Linear(256, 256)
        self.fc3 = nn.Linear(256, 400)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = torch.sigmoid(self.fc3(x))
        return x

# Load model
model = CharacterGenerator()
model.load_state_dict(torch.load('model.pth'))
model.eval()

# Generate all 256 characters (0-255)
all_chars = []
all_grids = []

print("Generating all 256 characters from PyTorch model...")

for ascii_code in range(256):
    # Create one-hot encoding (255 dimensions, skip one position)
    input_tensor = torch.zeros(1, 255)
    if ascii_code < 255:
        input_tensor[0, ascii_code] = 1.0
    # For ascii_code 255, all zeros (special case)
    
    # Generate character
    with torch.no_grad():
        output = model(input_tensor)
    
    # Convert to numpy and reshape to 20x20
    pixel_array = output.numpy().reshape(20, 20)
    
    # Count pixels (threshold at 0.5)
    pixel_count = int(np.sum(pixel_array > 0.5))
    
    all_chars.append({
        'ascii': ascii_code,
        'character': chr(ascii_code) if 32 <= ascii_code <= 126 else f'\\x{ascii_code:02x}',
        'pixels': pixel_count
    })
    
    all_grids.append(pixel_array)
    
    if (ascii_code + 1) % 32 == 0:
        print(f"Generated {ascii_code + 1}/256 characters...")

# Save as numpy array
all_grids_array = np.array(all_grids)
np.save('pytorch_all_256_chars.npy', all_grids_array)

# Save metadata
with open('pytorch_256_metadata.json', 'w') as f:
    json.dump(all_chars, f, indent=2)

# Create framebuffer format file (# and space)
with open('pytorch_256_framebuffers.txt', 'w') as f:
    for i, grid in enumerate(all_grids):
        char_info = all_chars[i]
        f.write(f"# Character {i} (ASCII {i}): {char_info['character']}\n")
        f.write(f"# Pixels: {char_info['pixels']}\n")
        
        for row in grid:
            line = ''.join(['#' if pixel > 0.5 else ' ' for pixel in row])
            f.write(line + '\n')
        
        f.write('\n')  # Blank line between characters

print(f"\n✅ Generated all 256 characters")
print(f"   - Saved: pytorch_all_256_chars.npy")
print(f"   - Saved: pytorch_256_metadata.json")
print(f"   - Saved: pytorch_256_framebuffers.txt")

# Print statistics
pixels = [c['pixels'] for c in all_chars]
print(f"\nStatistics:")
print(f"   Average pixels: {np.mean(pixels):.1f}")
print(f"   Min pixels: {min(pixels)}")
print(f"   Max pixels: {max(pixels)}")
