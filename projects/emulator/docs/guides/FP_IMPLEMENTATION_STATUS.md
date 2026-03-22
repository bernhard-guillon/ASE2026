# Floating-Point (F) Extension Implementation Status

## Overview

The RISC-V F Extension (32-bit floating-point) is partially implemented in the emulator to support neural network inference. This document tracks which FP instructions are supported and which are not.

## Supported F Extension Instructions

### Load/Store Operations
- **FLW** (Load FP): Load 32-bit float from memory into FP register
  - Opcode: 0x07, funct3: 0b010
  - Status: ✅ **Fully Implemented**

- **FSW** (Store FP): Store 32-bit float from FP register to memory
  - Opcode: 0x27, funct3: 0b010
  - Status: ✅ **Fully Implemented**

### Arithmetic Operations (OP-FP, Opcode 0x53)

#### Basic Arithmetic (funct7 = 0b0000000-0b0001100)
- **FADD.S** (funct7: 0b0000000): Float addition
  - Status: ✅ **Fully Implemented**
  - Essential for neural network computation

- **FSUB.S** (funct7: 0b0000100): Float subtraction
  - Status: ✅ **Fully Implemented**
  - Essential for neural network computation

- **FMUL.S** (funct7: 0b0001000): Float multiplication
  - Status: ✅ **Fully Implemented**
  - Essential for neural network layer computation

- **FDIV.S** (funct7: 0b0001100): Float division
  - Status: ✅ **Fully Implemented**
  - Used for normalization operations

#### Comparison Operations (funct7: 0b1010000)
- **FLE.S** (funct3: 0b000): Float less-than-or-equal (result in integer register)
  - Status: ✅ **Fully Implemented**
  - Used for conditional logic

- **FLT.S** (funct3: 0b001): Float less-than (result in integer register)
  - Status: ✅ **Fully Implemented**
  - Used for conditional logic

- **FEQ.S** (funct3: 0b010): Float equality (result in integer register)
  - Status: ✅ **Fully Implemented**
  - Used for convergence checks

#### Min/Max Operations (funct7: 0b0010100)
- **FMIN.S** (funct3: 0b000): Float minimum
  - Status: ✅ **Fully Implemented**
  - Used for ReLU-like activation functions

- **FMAX.S** (funct3: 0b001): Float maximum
  - Status: ✅ **Fully Implemented**
  - Essential for ReLU activation: `max(x, 0.0)`

#### Conversion Operations

- **FCVT.S.W** (funct7: 0b1101000, rs2: 0b00000): Convert signed integer to float
  - Status: ✅ **Fully Implemented**

- **FCVT.S.WU** (funct7: 0b1101000, rs2: 0b00001): Convert unsigned integer to float
  - Status: ✅ **Fully Implemented**

- **FCVT.W.S** (funct7: 0b1100000, rs2: 0b00000): Convert float to signed integer
  - Status: ✅ **Fully Implemented**
  - Uses current rounding mode

- **FCVT.WU.S** (funct7: 0b1100000, rs2: 0b00001): Convert float to unsigned integer
  - Status: ✅ **Fully Implemented**

#### Move Operations (funct7: 0b1110000)
- **FMV.W.X** (funct3: 0b000, rs2: 0b00000): Move bits from integer register to FP register
  - Status: ✅ **Fully Implemented**
  - Used for bitwise FP operations

- **FMV.X.W**: Move bits from FP register to integer register
  - Status: ❌ **Not Implemented**
  - Rarely used in neural network code

## Partially Supported / Known Limitations

### Soft-Float Library Dependencies
When compiling C code with GCC using `-march=rv32imf`, the compiler may generate calls to soft-float library functions for some operations:

- **Integer-to-Float Conversion** (in compound expressions): May use unsupported intermediate instructions
- **Float-to-Integer Conversion** (in certain contexts): May use unsupported library calls
- **Complex Float Operations**: Operations involving both FP and integer semantics may degrade to soft-float paths

**Workaround**: When testing FP functionality, use direct FP operations without mixed-type conversions. Avoid compiler-dependent optimizations by testing core operations (FADD, FMUL, FSUB) separately.

## Unsupported Operations

### Advanced FP Features
- **FSQRT.S**: Square root
- **FMADD.S / FMSUB.S / FNMADD.S / FNMSUB.S**: Fused multiply-add operations
- **FCLASS.S**: Float classification
- **Rounding Mode Control** (frm): All operations use default rounding mode

### Floating-Point Status/Exception Flags
- Exceptions are not generated or tracked
- Rounding modes (RNE, RTZ, RDN, RUP, RMM) are not fully implemented
- All operations implicitly use RNE (Round to Nearest Even)

## Testing Strategy

### For Core Neural Network Operations
Use **bitwise comparison** instead of floating-point equality (`==`):
```c
union {
    float f;
    unsigned int u;
} actual, expected;
actual.f = result;
expected.f = expected_value;
return actual.u == expected.u;
```

### For Compiler-Generated Code
Use **tolerance-based comparison** due to potential rounding differences:
```c
float epsilon = 0.0001f;
return (result - expected) < epsilon;
```

### Recommended Test Subset
- Focus on FADD.S, FSUB.S, FMUL.S, FMAX.S (for ReLU)
- Avoid FP-to-integer conversions in test expressions
- Avoid division in simple tests (may trigger soft-float paths)
- Test only the three essential operations for basic validation

## Performance Notes

- FP operations execute in 1 CPU cycle (no multicycle FP units)
- All FP registers (f0-f31) are standard 32-bit single-precision
- Memory operands are sign-extended immediately (no delay)
- No pipeline stalls or hazards modeled

## Future Work

1. **Implement FMV.X.W** for complete bit-manipulation support
2. **Add FSQRT.S** for normalization operations
3. **Implement rounding mode control** for advanced tests
4. **Add exception flags** for IEEE 754 compliance
5. **Optimize soft-float detection** to provide better error messages

## References

- [RISC-V ISA Specification v2.2](https://riscv.org/technical/specifications/)
- [RISC-V Floating-Point Environment](https://github.com/riscv/riscv-isa-manual)
