#!/usr/bin/env python3
"""Unit tests for neural operation reference semantics."""

import math
from neural_ops_oracle import (
    one_hot_255,
    matvec_io_f32,
    vec_relu_f32,
    sigmoid_piecewise_f32,
    vec_sigmoid_pwl_f32,
    vec_clamp_scale_u8_f32,
)


def test_one_hot_255_basic():
    vec = one_hot_255(65)
    assert len(vec) == 255
    assert vec[65] == 1.0
    assert sum(vec) == 1.0


def test_one_hot_255_out_of_range_is_all_zero():
    assert sum(one_hot_255(-1)) == 0.0
    assert sum(one_hot_255(255)) == 0.0


def test_sigmoid_piecewise_boundaries():
    assert sigmoid_piecewise_f32(-5.0) == 0.0
    assert sigmoid_piecewise_f32(-4.0) == 0.0
    assert sigmoid_piecewise_f32(0.0) == 0.5
    assert sigmoid_piecewise_f32(4.0) == 1.0
    assert sigmoid_piecewise_f32(10.0) == 1.0


def test_matvec_io_f32_layout_and_result():
    # input_len=2, output_len=2
    # weights_io = [w00, w01, w10, w11] = weights[i][j]
    inp = [1.0, 0.5]
    w = [2.0, -1.0, 3.0, 4.0]
    b = [0.5, -0.5]

    out = matvec_io_f32(inp, w, b)
    assert len(out) == 2
    assert abs(out[0] - 4.0) < 1e-6     # 0.5 + 1*2 + 0.5*3
    assert abs(out[1] - 0.5) < 1e-6     # -0.5 + 1*(-1) + 0.5*4


def test_vec_relu_f32():
    out = vec_relu_f32([-1.0, 0.0, 2.5])
    assert out == [0.0, 0.0, 2.5]


def test_vec_sigmoid_pwl_f32_vectorized():
    out = vec_sigmoid_pwl_f32([-8.0, -4.0, 0.0, 4.0, 8.0])
    assert out == [0.0, 0.0, 0.5, 1.0, 1.0]


def test_vec_clamp_scale_u8_f32_corner_cases():
    out = vec_clamp_scale_u8_f32([-1.0, 0.0, 0.5, 1.0, 2.0, float('nan'), float('inf'), float('-inf')])
    assert out == [0, 0, 127, 255, 255, 0, 255, 0]
    assert all(0 <= x <= 255 for x in out)


def test_dense_relu_flow_example():
    inp = [1.0, 0.0]
    w = [2.0, -1.0, 3.0, 4.0]
    b = [0.5, -0.5]
    dense = matvec_io_f32(inp, w, b)
    relu = vec_relu_f32(dense)
    assert dense[0] == 2.5
    assert dense[1] == -1.5
    assert relu == [2.5, 0.0]
