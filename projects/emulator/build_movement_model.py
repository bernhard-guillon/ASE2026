#!/usr/bin/env python3
"""
Build script for movement model - trains model if checkpoint doesn't exist and exports JSON.

This script is used by the CMake build system to ensure the movement model is available
for building the movement.elf target.
"""

import os
import sys
import subprocess

def main():
    # Get paths from environment variables (set by CMake)
    checkpoint_path = os.environ.get('MOVEMENT_MODEL_CHECKPOINT')
    train_script = os.environ.get('MOVEMENT_TRAIN_SCRIPT')
    export_script = os.environ.get('MOVEMENT_EXPORT_SCRIPT')
    output_path = os.environ.get('MOVEMENT_JSON_OUTPUT')
    
    if not all([checkpoint_path, train_script, export_script, output_path]):
        print("ERROR: Missing required environment variables")
        return 1
    
    # Check if checkpoint exists, if not train the model
    if not os.path.exists(checkpoint_path):
        print('Movement model checkpoint not found. Training model...')
        
        # Get the directory containing the train script
        train_dir = os.path.dirname(train_script)
        
        # Train the model (using default parameters: 150 epochs, batch size 64)
        result = subprocess.run([
            sys.executable, 'train.py', '150', '64'
        ], cwd=train_dir)
        
        if result.returncode != 0:
            print('ERROR: Failed to train movement model')
            return 1
    
    # Export the model to JSON format
    print('Exporting movement model to JSON...')
    result = subprocess.run([
        sys.executable, export_script, 
        '--checkpoint', checkpoint_path,
        '--output', output_path
    ])
    
    if result.returncode != 0:
        print('ERROR: Failed to export movement model')
        return 1
    
    print('Successfully generated movement model JSON')
    return 0

if __name__ == '__main__':
    sys.exit(main())