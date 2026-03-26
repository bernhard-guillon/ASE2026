#!/usr/bin/env python3
"""Reference semantics for planned neural operations.

These helpers define correctness contracts independent from ISA encoding.
"""

from __future__ import annotations

import math
import struct
from typing import Sequence, List


def f32(value: float) -> float:
    """Round a Python float to IEEE-754 float32."""
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


def one_hot_255(char_code: int) -> List[float]:
    """Return one-hot vector of length 255 with float32 entries."""
    out = [f32(0.0)] * 255
    if 0 <= char_code < 255:
        out[char_code] = f32(1.0)
    return out


def matvec_io_f32(input_vec: Sequence[float], weights_io: Sequence[float], bias: Sequence[float]) -> List[float]:
    """Dense matvec using current generated layout: weights[i][j]."""
    input_len = len(input_vec)
    output_len = len(bias)
    expected_weights = input_len * output_len
    if len(weights_io) != expected_weights:
        raise ValueError(f"weights_io size mismatch: got {len(weights_io)}, expected {expected_weights}")

    out: List[float] = []
    for j in range(output_len):
        acc = f32(bias[j])
        for i in range(input_len):
            x = f32(input_vec[i])
            w = f32(weights_io[i * output_len + j])
            acc = f32(acc + f32(x * w))
        out.append(acc)
    return out


def vec_relu_f32(values: Sequence[float]) -> List[float]:
    """Elementwise ReLU with float32 rounding."""
    out: List[float] = []
    for v in values:
        fv = f32(v)
        out.append(f32(fv if fv > 0.0 else 0.0))
    return out


def sigmoid_piecewise_f32(value: float) -> float:
    """Current generated sigmoid approximation: clamp(0.5 + x*0.125, 0, 1) with +-4 saturation."""
    x = f32(value)
    if x <= f32(-4.0):
        return f32(0.0)
    if x >= f32(4.0):
        return f32(1.0)
    return f32(f32(0.5) + f32(x * f32(0.125)))


def vec_sigmoid_pwl_f32(values: Sequence[float]) -> List[float]:
    """Elementwise sigmoid piecewise."""
    return [sigmoid_piecewise_f32(v) for v in values]


def clamp_scale_u8_f32(value: float) -> int:
    """Clamp float32 to [0,1], scale by 255, truncate toward zero to u8."""
    x = f32(value)
    if math.isnan(x):
        x = f32(0.0)
    if x < 0.0:
        x = f32(0.0)
    elif x > 1.0:
        x = f32(1.0)

    scaled = f32(x * f32(255.0))
    if not math.isfinite(scaled) or scaled < 0.0:
        return 0
    if scaled > 255.0:
        return 255
    return int(scaled)


def vec_clamp_scale_u8_f32(values: Sequence[float]) -> List[int]:
    """Vectorized clamp+scale conversion."""
    return [clamp_scale_u8_f32(v) for v in values]
