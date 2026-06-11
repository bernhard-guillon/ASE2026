# Block-Diagonal Model Composition

## What We Did

We combined two independent MLPs (counter + chargen) into a single model by:

1. **Concatenating their inputs** — each model reads from a disjoint slice of the combined input buffer
2. **Stacking weights block-diagonally** — each model's weight matrices become diagonal blocks in a larger combined matrix; off-diagonal blocks are zero
3. **Staging outputs** — the counter model's output is written to a buffer, then fed as input to the chargen model

This produces a single ELF that runs both models sequentially, with zero overhead compared to running them separately.

```
Input: [counter_input | chargen_input]
               |
    [W_counter    0    ]    block-diagonal
    [   0      W_chargen]    weight matrix
               |
    [counter_out | chargen_out]
               |
    counter_out → chargen_input  (staged)
               |
           chargen_out
```

## Existing Work (Yes, This Is a Known Technique)

### Block-Diagonal Weight Composition in Model Merging

**FS-Merge (Foldable SuperNets)** — Shwartz-Ziv et al., 2024
- Their "folding" step produces a block-diagonal merged weight matrix as an intermediate form:
  `W_l^* = M_l^* · [[W_l^A, 0], [0, W_l^B]] · U_{l-1}^*`
- This is a learnable generalization of our approach: they compose two models' weights block-diagonally, then apply learned merge/unmerge matrices.
- Paper: https://arxiv.org/abs/2410.01483

**Merging of Neural Networks** — Springer, 2024
- Explicitly describes "layerwise concatenation of teachers into a big student": concatenating weight matrices along the feature/channel dimension to create a wider network that simulates both teachers.
- No training needed for the concatenation step itself (just a network transformation).
- Paper: https://link.springer.com/article/10.1007/s11063-024-11445-y

### LoRA Concatenation

**LoRA-LEGO** — Wang et al., 2024
- Proves "Concatenation-Summation Equivalence": concatenating LoRA weight matrices `[A1; A2]` and `[B1, B2]` produces an output equal to the sum of the individual LoRA outputs.
- This is the same linear algebra property we rely on: block-diagonal composition equals running models independently.
- Paper: https://arxiv.org/abs/2409.16167

**CAT (Learnable Concatenation of LoRAs)** — COLING 2025
- Concatenates LoRA updates as `ΔW = α₁B₁A₁ᵀ + α₂B₂A₂ᵀ` to compose skills.
- Shows concatenation outperforms linear merging for compositional tasks.
- Paper: https://aclanthology.org/2025.coling-industry.55

### Practical Tools

**mergekit** — Arcee AI, 2023
- Popular open-source toolkit for merging LLMs.
- Includes a "passthrough" method that directly copies tensors from input models, used for "frankenmerging" (stacking layers from different models).
- A "block-diagonal" merge method was also proposed and discussed in the community.
- Repository: https://github.com/arcee-ai/MergeKit

**PyTorch `block_diag`** — Feature request since 2020
- The `torch.block_diag` function (now implemented) was motivated by graph neural networks needing to merge adjacency matrices into a large block-diagonal matrix.
- The same `scipy.linalg.block_diag` operation is widely used across scientific computing.

## Why It Works

For two independent models `A` and `B` with no shared parameters, composing them via block-diagonal weight concatenation is *exact*:

```
W_combined = blkdiag(W_A, W_B)
W_combined · [x_A; x_B] = [W_A · x_A;  W_B · x_B]
```

Staging (feeding `A`'s output as `B`'s input) is just function composition `B(A(x))`.

No approximation, no training, no alignment needed.

## When This Breaks

Block-diagonal composition only works when the models are *truly independent*:
- No shared layers or parameters
- Disjoint input features
- Sequential (staged) or parallel (independent) — but not cross-coupled

If the models share representations or need cross-talk between features, you need the more complex methods (learned projectors, weight alignment, task vector arithmetic, etc.).
