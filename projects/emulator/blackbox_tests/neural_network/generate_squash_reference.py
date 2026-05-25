#!/usr/bin/env python3
"""Generate reference binary for squash model forward pass.

Merges game_state + renderer via block-diagonal glue logic (matching
model_to_header Rust compiler), runs forward pass for the initial game
state, and writes a .bin file consumed by test_squash_model.cpp.

Binary format (all little-endian):
    uint32_t num_layers
    uint32_t input_size
    float[input_size]      input_values
  per layer:
    uint32_t in_sz
    uint32_t out_sz
    uint32_t activation    0=relu 1=sigmoid
    float[in_sz*out_sz]    weights (input-major row-major)
    float[out_sz]          biases
    float[out_sz]          pre_act    (matvec output before activation)
    float[out_sz]          post_act   (after activation)
"""

import json, struct, sys, numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent  # projects/emulator

def load_json(path):
    with open(str(path)) as f:
        return json.load(f)

def sigmoid_piecewise(x):
    r = np.zeros_like(x, dtype=np.float32)
    r[x <= -4.0] = 0.0
    m = (x > -4.0) & (x <= 0.0)
    r[m] = 0.5 + 0.125 * x[m]
    m = (x > 0.0) & (x <= 4.0)
    r[m] = 0.5 + 0.125 * x[m]
    r[x > 4.0] = 1.0
    return r

def act_code(name):
    if name == "relu": return 0
    if name == "sigmoid": return 1
    return 2  # none

def merge_layers(glue, models):
    merged = []
    for mldef in glue["merged_layers"]:
        total_in = 0
        total_out = 0
        block_overrides = []
        for b in mldef["blocks"]:
            l = models[b["model"]]["layers"][b["layer"]]
            ie = b.get("in_offset", 0) + l["input_size"]
            oe = b.get("out_offset", 0) + l["output_size"]
            if ie > total_in: total_in = ie
            if oe > total_out: total_out = oe
            # per-block activation override
            ba = b.get("activation") or mldef["activation"]
            if ba != mldef["activation"]:
                block_overrides.append(dict(offset=b.get("out_offset", 0), size=l["output_size"], activation=act_code(ba)))
        w = np.zeros((total_in, total_out), dtype=np.float64)
        b = np.zeros(total_out, dtype=np.float64)
        for blk in mldef["blocks"]:
            l = models[blk["model"]]["layers"][blk["layer"]]
            io = blk.get("in_offset", 0)
            oo = blk.get("out_offset", 0)
            w[io:io+l["input_size"], oo:oo+l["output_size"]] = np.array(l["weights"], dtype=np.float64)
            b[oo:oo+l["output_size"]] = np.array(l["biases"], dtype=np.float64)
        merged.append(dict(
            input_size=total_in, output_size=total_out,
            activation=act_code(mldef["activation"]),
            block_overrides=block_overrides,
            weights=np.array(w, dtype=np.float32),
            biases=np.array(b, dtype=np.float32),
        ))
    return merged

def make_initial_input():
    """Initial game state encoding (56 floats, same as MODEL_INPUT_SIZE)."""
    inp = np.zeros(56, dtype=np.float32)
    # ball_x = 10 (one-hot at index 10 of 20)
    inp[10] = 1.0
    # ball_y = 7 (one-hot at index 7 of 15)
    inp[20 + 7] = 1.0
    # paddle_y = 3 (one-hot at index 3 of 11)
    inp[20 + 15 + 3] = 1.0
    # game_state = 0 (one-hot at index 0 of 2)
    inp[20 + 15 + 11 + 0] = 1.0
    # ball_vx = 1 (one-hot at index 1 of 2) — moving right
    inp[20 + 15 + 11 + 2 + 1] = 1.0
    # ball_vy = 0 (one-hot at index 0 of 2) — no vertical movement
    inp[20 + 15 + 11 + 2 + 2 + 0] = 1.0
    # No keys pressed: buf[52] and buf[54] remain 0 (matching MODEL_MAP_INPUT)
    return inp

def apply_activation(arr, act):
    if act == 0:
        return np.maximum(arr, 0.0)
    elif act == 1:
        return sigmoid_piecewise(arr)
    else:  # none
        return arr.copy()

def run_forward(merged, inp):
    inputs = inp.copy()
    results = []
    for layer in merged:
        logits = inputs @ layer["weights"] + layer["biases"]
        # Apply main activation to entire output
        out = apply_activation(logits, layer["activation"])
        # Apply per-block overrides (overwrite main activation for specific ranges)
        for ov in layer.get("block_overrides", []):
            o_off = ov["offset"]
            o_sz = ov["size"]
            o_act = ov["activation"]
            out[o_off:o_off+o_sz] = apply_activation(logits[o_off:o_off+o_sz], o_act)
        results.append(dict(
            input_size=layer["input_size"],
            output_size=layer["output_size"],
            activation=layer["activation"],
            block_overrides=layer.get("block_overrides", []),
            weights=layer["weights"],
            biases=layer["biases"],
            pre_act=np.array(logits, dtype=np.float32),
            post_act=np.array(out, dtype=np.float32),
        ))
        inputs = out
    return results

def write_bin(path, inp, layer_results):
    with open(str(path), "wb") as f:
        def wu32(v): f.write(struct.pack("<I", v))
        def wf32(v): f.write(struct.pack("<f", v))
        wu32(len(layer_results))
        wu32(len(inp))
        for v in inp: wf32(v)
        for lr in layer_results:
            wu32(lr["input_size"])
            wu32(lr["output_size"])
            wu32(lr["activation"])
            for v in lr["weights"].flat: wf32(v)
            for v in lr["biases"]: wf32(v)
            for v in lr["pre_act"]: wf32(v)
            for v in lr["post_act"]: wf32(v)
            block_ovs = lr.get("block_overrides", [])
            wu32(len(block_ovs))
            for ov in block_ovs:
                wu32(ov["offset"])
                wu32(ov["size"])
                wu32(ov["activation"])

def main():
    import sys
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "build"
    out_path = out_dir / "squash_model_ref.bin"
    glue = load_json(HERE / "squash_glue.json")
    models = {}
    for mref in glue["models"]:
        path = HERE / mref["path"]
        models[mref["name"]] = load_json(path)
    merged = merge_layers(glue, models)
    inp = make_initial_input()
    results = run_forward(merged, inp)
    write_bin(out_path, inp, results)
    print(f"Wrote {out_path}")
    # Quick self-check: print final output stats
    last = results[-1]
    print(f"  Layer 0: {results[0]['input_size']}->{results[0]['output_size']}, "
          f"post_act min={results[0]['post_act'].min():.4f} max={results[0]['post_act'].max():.4f}")
    print(f"  Layer 1: {results[1]['input_size']}->{results[1]['output_size']}, "
          f"post_act min={results[1]['post_act'].min():.4f} max={results[1]['post_act'].max():.4f}")
    print(f"  Layer 2: {results[2]['input_size']}->{results[2]['output_size']}, "
          f"pre_act  min={last['pre_act'].min():.4f} max={last['pre_act'].max():.4f}")
    print(f"  Layer 2 post_act min={last['post_act'].min():.4f} max={last['post_act'].max():.4f}")
    # Check if any pre_act values in final layer are >= 4.0 (would saturate PWL sigmoid)
    n_saturated = np.sum(last["pre_act"] >= 4.0)
    n_total = len(last["pre_act"])
    print(f"  Layer 2 pre_act >= 4.0: {n_saturated}/{n_total}")
    if n_saturated == n_total:
        print("  ⚠  ALL pre_act values saturated! This would explain all-1.0 output.")
    elif n_saturated > 0:
        print(f"  ⚠  {n_saturated}/{n_total} pre_act values saturated.")

if __name__ == "__main__":
    main()
