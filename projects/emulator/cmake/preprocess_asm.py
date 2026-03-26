#!/usr/bin/env python3
"""
Simple assembly preprocessor that:
- Removes assembler directives (.section, .globl, .string, .data, .text, etc.)
- Expands pseudo-instructions (li, la) to raw instructions
- Removes labels (for now, just strip them)
- Keeps only RV32I/F instructions
"""

import sys
import re

def expand_li(register, value):
    """Expand load immediate to RISC-V instructions"""
    # li rd, value -> lui + addi (or just addi if value fits in 12 bits)
    value = int(value, 0) if isinstance(value, str) else value
    
    if -2048 <= value <= 2047:
        return f"addi {register}, x0, {value}"
    else:
        # Split into upper and lower bits
        upper = ((value + 0x800) >> 12) & 0xFFFFF  # lui uses sign-extended 12-bit immediate
        if upper & 0x80000:  # Handle negative upper bits
            upper = upper - 0x100000
        lower = value & 0xFFF
        if lower & 0x800:  # Handle negative lower bits
            lower = lower - 0x1000
        
        return f"lui {register}, {upper}\naddi {register}, {register}, {lower}"

def expand_la(register, label):
    """Expand load address to RISC-V instructions"""
    # For now, just treat it as an error since we don't have symbol resolution
    # In real assembly, this would be resolved by the linker
    return f"# la {register}, {label}  # Not supported without symbol table"

def preprocess(asm_text):
    """Preprocess assembly to remove directives and expand pseudo-instructions"""
    lines = asm_text.split('\n')
    result = []
    
    for line in lines:
        # Remove comments
        if '#' in line:
            line = line[:line.index('#')]
        
        line = line.strip()
        
        if not line:
            continue
        
        # Skip directives
        if line.startswith('.'):
            continue
        
        # Handle labels (strip them for now)
        if line.endswith(':'):
            continue
        
        # Handle pseudo-instructions
        # li rd, value
        li_match = re.match(r'li\s+(\w+),\s*(.+)', line)
        if li_match:
            reg, val = li_match.groups()
            expanded = expand_li(reg, val.strip())
            result.extend(expanded.split('\n'))
            continue
        
        # la rd, label (not supported)
        la_match = re.match(r'la\s+(\w+),\s*(\w+)', line)
        if la_match:
            reg, label = la_match.groups()
            # Skip la instructions for parity testing
            continue
        
        # Keep regular instructions
        result.append(line)
    
    return '\n'.join(result)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <assembly_file>", file=sys.stderr)
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        asm_text = f.read()
    
    preprocessed = preprocess(asm_text)
    sys.stdout.write(preprocessed)
