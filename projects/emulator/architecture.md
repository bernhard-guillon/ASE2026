# Combined Counter-Character Generator Architecture

## Overview

This document describes the **3-layer combined network architecture** where a counter network and a character generator network run in parallel, processing the same input simultaneously.

### Goal
- Both networks (counter and chargen) must have the same layer depth (3 layers each)
- Both networks process the same initial input (one-hot encoded ASCII character from register `a0`)
- The counter does **not** change the input register (`a0`) — it maintains its own state
- Both networks' layers transition to the next layer at the same time (synchronized)
- The output of the combined network must match the standalone character generator's output

---

## Architecture

### Individual Networks

**Counter Network (3 layers):**
```
Layer 0: counter255_layer0 - 255 → 256
Layer 1: counter255_layer1 - 256 → 256  
Layer 2: counter255_layer2 - 256 → 255
```
*Function: Deterministic modulo-255 counter (output = (input + 1) mod 255)*

**Character Generator Network (3 layers):**
```
Layer 0: layer_0 - 255 → 256
Layer 1: layer_1 - 256 → 256
Layer 2: layer_2 - 256 → 400
```
*Function: Maps ASCII character to 20×20 pixel framebuffer (400 values)*

### Combined Network (3 layers with disconnected sub-networks)

The combined network is structured as a **single 3-layer network** where each layer contains two independent sub-networks with **zero cross-connections**.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COMBINED NETWORK (3 Layers)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input: 255 neurons (one-hot ASCII encoding from register a0)        │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │ Layer 0                  │    │ Layer 0                  │         │
│  │ Counter sub-network     │    │ Chargen sub-network      │         │
│  │ 255 → 256 neurons        │    │ 255 → 256 neurons        │         │
│  │ (weights from counter L0)│    │ (weights from chargen L0)│         │
│  └──────────┬──────────────┘    └──────────┬──────────────┘         │
│             │                              │                            │
│             ▼                              ▼                            │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │ Layer 1                  │    │ Layer 1                  │         │
│  │ Counter sub-network     │    │ Chargen sub-network      │         │
│  │ 256 → 256 neurons        │    │ 256 → 256 neurons        │         │
│  │ (weights from counter L1)│    │ (weights from chargen L1)│         │
│  └──────────┬──────────────┘    └──────────┬──────────────┘         │
│             │                              │                            │
│             ▼                              ▼                            │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │ Layer 2                  │    │ Layer 2                  │         │
│  │ Counter sub-network     │    │ Chargen sub-network      │         │
│  │ 256 → 255 neurons        │    │ 256 → 400 neurons        │         │
│  │ (weights from counter L2)│    │ (weights from chargen L2)│         │
│  └──────────┬──────────────┘    └──────────┬──────────────┘         │
│             │                              │                            │
│             ▼                              ▼                            │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │ Counter Output          │    │ Framebuffer Output       │         │
│  │ 255 neurons              │    │ 400 neurons (20×20)     │         │
│  │ (stored in debug memory)│    │ → Written to 0x20000     │         │
│  └─────────────────────────┘    └─────────────────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer Dimensions Summary

| Layer | Counter Sub-Network | Chargen Sub-Network | Total Input | Total Output |
|-------|---------------------|---------------------|-------------|--------------|
| 0     | 255 → 256           | 255 → 256           | 255         | 512 (256+256) |
| 1     | 256 → 256           | 256 → 256           | 512         | 512 (256+256) |
| 2     | 256 → 255           | 256 → 400           | 512         | 655 (255+400) |

**Note:** Only the chargen output (400 neurons from Layer 2) is written to the framebuffer at `0x20000`. The counter output (255 neurons) is stored separately in debug memory.

---

## Weight Matrix Structure

Each layer's weight matrix is a **block-diagonal matrix** with zero weights between the counter and chargen sub-networks.

### Layer 0: 255 → 512

**Weight matrix W₀ (255 × 512):**
```
[ Counter L0 weights (255×256) | Chargen L0 weights (255×256) ]
```
- Left 255×256 block: Non-zero weights for counter Layer 0
- Right 255×256 block: Non-zero weights for chargen Layer 0
- All other entries: **Zero** (no cross-connections)

**Bias vector b₀ (512):**
```
[ Counter L0 biases (256) | Chargen L0 biases (256) ]
```

### Layer 1: 512 → 512

**Weight matrix W₁ (512 × 512) — Block-diagonal:**
```
[ Counter L1 weights (256×256)    0 (256×256)     ]
[ 0 (256×256)               Chargen L1 weights (256×256) ]
```
- Top-left 256×256: Counter Layer 1 weights
- Bottom-right 256×256: Chargen Layer 1 weights
- Off-diagonal blocks: **All zeros**

**Bias vector b₁ (512):**
```
[ Counter L1 biases (256) | Chargen L1 biases (256) ]
```

### Layer 2: 512 → 655

**Weight matrix W₂ (512 × 655) — Block-diagonal:**
```
[ Counter L2 weights (256×255)    0 (256×400)     ]
[ 0 (256×255)               Chargen L2 weights (256×400) ]
```
- Top-left 256×255: Counter Layer 2 weights
- Bottom-right 256×400: Chargen Layer 2 weights
- Off-diagonal blocks: **All zeros**

**Bias vector b₂ (655):**
```
[ Counter L2 biases (255) | Chargen L2 biases (400) ]
```

---

## Data Flow

### Forward Pass

Given input vector `x ∈ ℝ²⁵⁵` (one-hot encoded ASCII):

**Layer 0:**
```
h₀ = ReLU(W₀ · x + b₀)
  = [ReLU(W₀_counter · x + b₀_counter), ReLU(W₀_chargen · x + b₀_chargen)]
  = [h₀_counter (256), h₀_chargen (256)]
```

**Layer 1:**
```
h₁ = ReLU(W₁ · h₀ + b₁)
  = [ReLU(W₁_counter · h₀_counter + b₁_counter), ReLU(W₁_chargen · h₀_chargen + b₁_chargen)]
  = [h₁_counter (256), h₁_chargen (256)]
```
*Note: W₁'s off-diagonal blocks are zero, so counter path only depends on h₀_counter, and chargen path only on h₀_chargen*

**Layer 2:**
```
h₂ = σ(W₂ · h₁ + b₂)  (σ = sigmoid for chargen, none for counter)
  = [σ(W₂_counter · h₁_counter + b₂_counter), σ(W₂_chargen · h₁_chargen + b₂_chargen)]
  = [h₂_counter (255), h₂_chargen (400)]
```

**Output:**
- Framebuffer = h₂_chargen (400 values) → address `0x20000`
- Counter state = h₂_counter (255 values) → debug memory `0x00153FE0` (NOT written to `a0`)

---

## Key Properties

### ✅ Why This Works

1. **Mathematically valid**: Block-diagonal weight matrices with zero off-diagonal elements are standard in neural networks
2. **True parallelism**: Both sub-networks process independently within each layer
3. **Same initial input**: Both networks receive the same one-hot input from `a0`
4. **No cross-talk**: Zero weights between sub-networks ensure complete independence
5. **Preserved behavior**: Chargen output is identical to standalone network (same weights, same input)

### ✅ Compatibility

- Standard neural network architecture (no custom operations needed)
- Works with existing model compiler (just needs wider layer dimensions)
- Works with existing emulator (no architectural changes)

### ⚠️ Implementation Notes

- The counter network's **final output is not used to modify `a0`** — it's stored in debug memory only
- The chargen network's **input is always the original one-hot from `a0`**, not affected by counter state
- Both networks run **synchronized**: Layer i of counter and Layer i of chargen execute together

---

## Layer Indexing and Buffer Layout

### Buffer Addresses

| Buffer | Address | Size | Purpose |
|--------|---------|------|---------|
| Input | 0x00150000 | 255×4 bytes | One-hot input (from `a0`) |
| Activation A | 0x00151000 | 512×4 bytes | Layer 0 output (256 counter + 256 chargen) |
| Activation B | 0x00152000 | 512×4 bytes | Layer 1 output (256 counter + 256 chargen) |
| Output | 0x00153000 | 655×4 bytes | Layer 2 output (255 counter + 400 chargen) |
| Framebuffer | 0x0020000 | 400 bytes | Chargen output (last 400 of Output buffer) |
| Debug | 0x00153FE0 | 4 bytes | Counter state (argmax result) |

### Buffer Usage Per Layer

**Layer 0 (255 → 512):**
- Input: 0x00150000 (255 floats)
- Output: 0x00151000 (512 floats: 256 counter + 256 chargen)

**Layer 1 (512 → 512):**
- Input: 0x00151000 (512 floats)
- Output: 0x00152000 (512 floats: 256 counter + 256 chargen)

**Layer 2 (512 → 655):**
- Input: 0x00152000 (512 floats)
- Output: 0x00153000 (655 floats: 255 counter + 400 chargen)

---

## Model Generation

### Files Created

1. **`export_counter255_three_layer.py`** - Exports 3-layer counter model
2. **`export_counter_char_combined_3layer.py`** - Composes 3-layer counter + 3-layer chargen
3. **`build/counter255_three_layer.json`** - 3-layer counter model JSON
4. **`build/counter-char-combined-3layer-parallel.json`** - Combined model JSON

### Composition Logic

The combined model JSON is created by:
1. Taking all 3 layers from the counter model
2. Taking all 3 layers from the chargen model
3. Combining them into a single model with 6 layers (sequential)
4. **Future work**: Re-structure as 3 layers with block-diagonal weights

### Current Limitation

The current combined model (6 sequential layers) does **not** yet implement the block-diagonal architecture. It still runs counter layers first, then chargen layers. To achieve true parallelism, the model compiler needs to be updated to:
1. Accept the 6-layer sequential model
2. Re-map it to 3 layers with block-diagonal weight matrices
3. Generate assembly that processes both sub-networks in parallel within each layer

---

## Expected Behavior

When the network runs with `a0 = 97` (ASCII 'a'):

1. **Input**: One-hot vector at position 97 (255-dim)
2. **Layer 0**: Both sub-networks process independently
   - Counter L0: Shifts one-hot to position (97+1) mod 255 = 98
   - Chargen L0: Transforms one-hot at 97 to 256-dim representation
3. **Layer 1**: Both sub-networks continue independently
   - Counter L1: Identity transformation (256→256)
   - Chargen L1: Further transformation (256→256)
4. **Layer 2**: Both sub-networks produce final output
   - Counter L2: Projects to 255-dim (final counter state)
   - Chargen L2: Projects to 400-dim (20×20 pixel grid)
5. **Output**: Chargen's 400 values → framebuffer at `0x20000`

**Result**: Framebuffer should be **identical** to standalone chargen network with `a0=97`.

---

## Summary

This architecture achieves true parallel execution of counter and character generator networks by:
- Combining them into a single 3-layer network
- Using block-diagonal weight matrices to keep sub-networks independent
- Maintaining separate data paths within each layer
- Only using the chargen output for the framebuffer

This is a **valid, standard neural network** that requires no special hardware or compiler support — just appropriate weight matrix construction.
