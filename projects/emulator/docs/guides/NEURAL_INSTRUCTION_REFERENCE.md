# Neural Instruction Reference (Draft)

## Status

This is a **specification draft** for planned neural instructions.

- Syntax and semantics in this file are the source of truth for implementation.
- Final opcode/funct field encodings are intentionally deferred until assembler Phase C.
- All instructions are designed to be deterministic and side-effect minimal.

## 1. Conventions

### 1.1 Notation

- `rs*` / `rd`: integer registers carrying addresses, counts, or status.
- `f32`: IEEE-754 single precision.
- `u8`: unsigned byte.
- Memory addresses are byte addresses.
- `len` counts **elements**, not bytes.

### 1.2 Error model

For the first implementation pass (correctness-first):

- Invalid pointers/lengths/alignment must return a non-zero status in `rd_status`.
- No silent fallback behavior.
- No partial writes when precondition validation fails.

### 1.3 Determinism rules

- Execution is deterministic for equal inputs/memory state.
- No hidden randomization.
- No data-dependent undefined behavior.

## 2. Instruction summary

| Instruction | Category | Purpose |
|---|---|---|
| `NMATVEC.F32` | Tensor | Dense matrix-vector + bias |
| `NVRELU.F32` | Vector | Elementwise ReLU |
| `NVSIGPWL.F32` | Vector | Elementwise piecewise sigmoid |
| `NVCLAMPU8.F32` | Vector | Clamp `[0,1]`, scale to `[0,255]`, store `u8` |

## 3. Instruction details

---

## 3.1 `NMATVEC.F32`

### Syntax

```asm
NMATVEC.F32 rd_status, rs_desc
```

### Purpose

Compute one dense layer output:

```text
out[j] = bias[j] + sum(i=0..input_len-1) input[i] * weight_io[i][j]
```

### Descriptor layout (`rs_desc` points here)

All fields are little-endian `u32`:

| Offset | Name | Meaning |
|---:|---|---|
| `+0x00` | `input_ptr` | `f32[input_len]` |
| `+0x04` | `weights_ptr` | `f32[input_len * output_len]`, input-major (`i*output_len+j`) |
| `+0x08` | `bias_ptr` | `f32[output_len]` |
| `+0x0C` | `output_ptr` | `f32[output_len]` |
| `+0x10` | `input_len` | number of input elements |
| `+0x14` | `output_len` | number of output elements |
| `+0x18` | `flags` | reserved (must be zero for v1) |
| `+0x1C` | `reserved` | reserved |

### Operation

```text
if !valid(desc): rd_status = ERR; return
for j in [0, output_len):
    acc = f32(bias[j])
    for i in [0, input_len):
        acc = f32(acc + f32(input[i] * weights[i*output_len + j]))
    output[j] = acc
rd_status = 0
```

### Constraints

- `input_ptr`, `weights_ptr`, `bias_ptr`, `output_ptr` must be 4-byte aligned.
- `flags != 0` is invalid for v1.
- Overlap between `weights` and `output` is invalid.

### Notes

- This instruction mirrors the current generated scalar dense loop exactly.
- Activation is intentionally separate (compose with `NVRELU.F32` or `NVSIGPWL.F32`).

### Example

```asm
la   t0, dense0_desc
NMATVEC.F32 t1, t0      # t1 = status
bnez t1, neural_fault
```

---

## 3.2 `NVRELU.F32`

### Syntax

```asm
NVRELU.F32 rd_status, rs_dst, rs_src, rs_len
```

### Purpose

Elementwise ReLU transform:

```text
dst[i] = max(src[i], 0.0)
```

### Operation

```text
if !valid(ptrs,len): rd_status = ERR; return
for i in [0, len):
    x = f32(src[i])
    dst[i] = f32(max(x, 0.0))
rd_status = 0
```

### Constraints

- `dst` and `src` may alias (in-place allowed).
- `dst` and `src` must be 4-byte aligned.

### Example

```asm
NVRELU.F32 t0, a1, a1, a2   # in-place ReLU over a2 elements
```

---

## 3.3 `NVSIGPWL.F32`

### Syntax

```asm
NVSIGPWL.F32 rd_status, rs_dst, rs_src, rs_len
```

### Purpose

Apply current model-compatible piecewise sigmoid approximation:

```text
x <= -4 -> 0
x >=  4 -> 1
else    -> 0.5 + x*0.125
```

### Operation

```text
if !valid(ptrs,len): rd_status = ERR; return
for i in [0, len):
    x = f32(src[i])
    if x <= -4.0: y = 0.0
    else if x >= 4.0: y = 1.0
    else: y = f32(0.5 + f32(x * 0.125))
    dst[i] = y
rd_status = 0
```

### Constraints

- In-place allowed.
- 4-byte alignment required.

### Example

```asm
NVSIGPWL.F32 t0, s2, s2, s3
```

---

## 3.4 `NVCLAMPU8.F32`

### Syntax

```asm
NVCLAMPU8.F32 rd_status, rs_dst_u8, rs_src_f32, rs_len
```

### Purpose

Convert float outputs to framebuffer bytes:

```text
x = clamp(x, 0, 1)
out = trunc(x * 255)
```

### Operation

```text
if !valid(ptrs,len): rd_status = ERR; return
for i in [0, len):
    x = f32(src[i])
    if isnan(x): x = 0.0
    if x < 0.0: x = 0.0
    if x > 1.0: x = 1.0
    y = f32(x * 255.0)
    dst[i] = u8(trunc_toward_zero(y))
rd_status = 0
```

### Constraints

- `src_f32` must be 4-byte aligned.
- `dst_u8` may be byte-aligned.

### Example

```asm
NVCLAMPU8.F32 t0, a0, a1, a2   # framebuffer <- float output
```

---

## 4. Composition pattern for current model

```text
NMATVEC.F32  (layer0) -> NVRELU.F32
NMATVEC.F32  (layer1) -> NVRELU.F32
NMATVEC.F32  (layer2) -> NVSIGPWL.F32
NVCLAMPU8.F32 -> framebuffer
```

## 5. Compatibility requirements

A compliant implementation must match current scalar path behavior for:

- one inference step result,
- piecewise sigmoid boundaries (`-4`, `4`),
- output byte mapping (`0..255`),
- deterministic repeatability.

## 6. Future extensions (reserved)

Planned but not part of v1 semantics:

- fused `NMATVEC_ACT.F32`
- block/tiled matvec variants
- SIMD lane-width variants
- quantized integer kernels
