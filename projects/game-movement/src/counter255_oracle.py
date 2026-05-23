"""
Oracle for modulo-255 counter transitions.

Contract:
- state is a scalar integer in [0, 254]
- next_state = (state + 1) % 255
"""

from __future__ import annotations


COUNTER255_MODULUS = 255


def counter255_step(state: int) -> int:
    """Return the next counter state with modulo-255 wrap."""
    if not (0 <= state < COUNTER255_MODULUS):
        raise ValueError(f"state must be in [0, {COUNTER255_MODULUS - 1}], got {state}")
    return (state + 1) % COUNTER255_MODULUS

