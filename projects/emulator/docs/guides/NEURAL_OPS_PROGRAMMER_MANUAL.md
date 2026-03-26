# Neural Ops Programmer Manual (Foundation Draft)

## 1. Purpose

This document defines a correctness-first contract for neural/tensor-style operations we plan to add to the emulator path.

The goal is to provide unambiguous semantics before ISA and assembler work starts, so implementation and tests share one reference.

## 2. Current neural execution (reference behavior)

Current generated neural code executes a scalar loop pipeline:

```text
a0 char -> one-hot input[255]
        -> Dense(255x256) + ReLU
        -> Dense(256x256) + ReLU
        -> Dense(256x400) + sigmoid_piecewise
        -> clamp[0..1], scale*255, store framebuffer[400]
        -> repeat
```

Dataflow diagram:

```text
+-------------------+      +--------------------------+
| map_input_generator| ---> | activation_a (layer 0)   |
| one-hot at 0x150000|      +--------------------------+
+-------------------+                    |
                                          v
                                +--------------------------+
                                | activation_b (layer 1)   |
                                +--------------------------+
                                          |
                                          v
                                +--------------------------+
                                | output (layer 2)         |
                                | 0x153000 (400 x f32)     |
                                +--------------------------+
                                          |
                                          v
                                +--------------------------+
                                | framebuffer 0x20000      |
                                | 400 x u8                 |
                                +--------------------------+
```

Control-flow diagram:

```text
inference_loop:
  map_input
  run_forward_pass
    layer_0
    layer_1
    layer_2
  map_output
  j inference_loop
```

## 3. Proposed operation set (emulator-level)

Status legend:
- **Specified**: semantics frozen in this manual.
- **Not yet implemented**: instruction decode/execute not wired yet.

### 3.1 MATVEC_F32 (specified)

Compute dense output with input-major weights (compatible with current generated layout):

```text
out[j] = bias[j] + sum(i=0..input_len-1) input[i] * weight_io[i][j]
```

Where weight storage is linearized as:

```text
weights_io[i * output_len + j]
```

Inputs:
- `input`: `input_len` float32 values
- `weights_io`: `input_len * output_len` float32 values
- `bias`: `output_len` float32 values

Output:
- `out`: `output_len` float32 values

Contract:
- Computation is float32 with per-op float32 rounding behavior.
- No implicit activation.
- No in-place overlap between `out` and `weights_io`.

### 3.2 VEC_RELU_F32 (specified)

```text
y[i] = max(x[i], 0.0)
```

Contract:
- Float32 semantics.
- In-place allowed (`y` may alias `x`).

### 3.3 VEC_SIGMOID_PWL_F32 (specified)

Compatibility target: current `sigmoid_piecewise` codegen behavior.

```text
if x <= -4.0: y = 0.0
else if x >= 4.0: y = 1.0
else: y = 0.5 + x * 0.125
```

Contract:
- Float32 semantics.
- Piecewise approximation by design (not exp sigmoid).
- In-place allowed.

### 3.4 VEC_CLAMP_SCALE_U8 (specified)

Convert float output to framebuffer bytes.

```text
clamped = clamp(x, 0.0, 1.0)
scaled = clamped * 255.0
out_u8 = trunc_toward_zero(scaled)
```

Contract:
- Output range is `[0, 255]`.
- NaN policy (for oracle/tests): treat as `0.0` before scaling.
- In-place not applicable (`f32 -> u8`).

## 4. Memory and safety rules

- All pointers must be valid for full operation length.
- Alignment target: 4-byte aligned for float32 buffers.
- No silent wraparound on byte counts/offsets.
- Any future instruction implementation should fail loudly for invalid forms.

## 5. Numeric behavior

- Reference domain is IEEE-754 single precision.
- Test oracle rounds to float32 at operation boundaries.
- Exact bit-match with host FPU is not guaranteed for every corner case, but operation-level expectations are fixed by tests.

## 6. Programmer-facing pseudocode

```text
# dense + relu block
matvec_f32(input, weights_io, bias, out)
vec_relu_f32(out)

# final layer + sigmoid + framebuffer conversion
matvec_f32(input2, weights2_io, bias2, out2)
vec_sigmoid_pwl_f32(out2)
vec_clamp_scale_u8(out2, fb)
```

## 7. Testing strategy (foundation)

Phase-A test scaffolding includes:
- `test_neural_ops_oracle.py`: reference semantics tests.
- `test_assembler_dropin_parity_scaffold.py`: parity harness skeleton against GNU assembler.

When new ops are implemented, these become the first regression barrier.
