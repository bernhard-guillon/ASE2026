import sys
sys.path.insert(0, '.')
from model_compiler import ModelCompiler

# Create compiler with test addresses
compiler = ModelCompiler(verbose=True)

# Override memory layout with safe test addresses
compiler.MEMORY_LAYOUT = {
    "code_base": 0x00000000,
    "generator_base": 0x00000300,      # Safe offset after .data
    "recognizer_base": 0x00000400,
    "buffer_base": 0x00000300,         # Same as generator since we're testing generator
    "framebuffer_base": 0x00000400,
}

compiler.BUFFER_OFFSETS = {
    "input": 0x0000,           # 0x300
    "activation_a": 0x0100,    # 0x400  
    "activation_b": 0x0200,    # 0x500
    "output": 0x0300,          # 0x600
}

# Compile
asm_path, bin_path = compiler.compile('blackbox_tests/neural_exec/test_simple_layer.json', 
                                      'test_safe.s',
                                      with_bootloader=False)
print(f"Generated: {asm_path}")
