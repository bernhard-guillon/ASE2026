"""
Reference squash physics: deterministic ball + paddle + out detection.
All coordinates in 20-wide × 15-tall game grid.
"""

BALL_X_RANGE = 20   # 0..19
BALL_Y_RANGE = 15   # 0..14
BALL_V_RANGE = 2    # 0=left/up, 1=right/down
PADDLE_Y_RANGE = 11 # 0..10 (paddle is 5 tall)
GAME_STATE_RANGE = 2 # 0=live, 1=lost
KEY_RANGE = 2       # 0=released, 1=pressed

PADDLE_HEIGHT = 5

INPUT_SIZE = BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE + BALL_V_RANGE + BALL_V_RANGE + KEY_RANGE + KEY_RANGE  # 56
OUTPUT_SIZE = BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE + BALL_V_RANGE + BALL_V_RANGE  # 52

# Input layout indices
I_BALL_X = 0
I_BALL_Y = I_BALL_X + BALL_X_RANGE
I_PADDLE_Y = I_BALL_Y + BALL_Y_RANGE
I_GAME_STATE = I_PADDLE_Y + PADDLE_Y_RANGE
I_BALL_VX = I_GAME_STATE + GAME_STATE_RANGE
I_BALL_VY = I_BALL_VX + BALL_V_RANGE
I_KEY_UP = I_BALL_VY + BALL_V_RANGE
I_KEY_DOWN = I_KEY_UP + KEY_RANGE
assert I_KEY_DOWN + KEY_RANGE == INPUT_SIZE

# Output layout indices
O_BALL_X = 0
O_BALL_Y = O_BALL_X + BALL_X_RANGE
O_PADDLE_Y = O_BALL_Y + BALL_Y_RANGE
O_GAME_STATE = O_PADDLE_Y + PADDLE_Y_RANGE
O_BALL_VX = O_GAME_STATE + GAME_STATE_RANGE
O_BALL_VY = O_BALL_VX + BALL_V_RANGE
assert O_BALL_VY + BALL_V_RANGE == OUTPUT_SIZE


def one_hot(index, size):
    vec = [0.0] * size
    vec[index] = 1.0
    return vec


def argmax(vec):
    return max(range(len(vec)), key=lambda i: vec[i])


def decode_state(one_hot_vec):
    bx = argmax(one_hot_vec[I_BALL_X:I_BALL_X + BALL_X_RANGE])
    by = argmax(one_hot_vec[I_BALL_Y:I_BALL_Y + BALL_Y_RANGE])
    py = argmax(one_hot_vec[I_PADDLE_Y:I_PADDLE_Y + PADDLE_Y_RANGE])
    gs = argmax(one_hot_vec[I_GAME_STATE:I_GAME_STATE + GAME_STATE_RANGE])
    vx = argmax(one_hot_vec[I_BALL_VX:I_BALL_VX + BALL_V_RANGE])
    vy = argmax(one_hot_vec[I_BALL_VY:I_BALL_VY + BALL_V_RANGE])
    ku = argmax(one_hot_vec[I_KEY_UP:I_KEY_UP + KEY_RANGE])
    kd = argmax(one_hot_vec[I_KEY_DOWN:I_KEY_DOWN + KEY_RANGE])
    return bx, by, vx, vy, py, gs, ku, kd


def encode_input(bx, by, vx, vy, py, gs, ku, kd):
    vec = [0.0] * INPUT_SIZE
    for idx, (val, size, base) in enumerate([
        (bx, BALL_X_RANGE, I_BALL_X),
        (by, BALL_Y_RANGE, I_BALL_Y),
        (py, PADDLE_Y_RANGE, I_PADDLE_Y),
        (gs, GAME_STATE_RANGE, I_GAME_STATE),
        (vx, BALL_V_RANGE, I_BALL_VX),
        (vy, BALL_V_RANGE, I_BALL_VY),
        (ku, KEY_RANGE, I_KEY_UP),
        (kd, KEY_RANGE, I_KEY_DOWN),
    ]):
        vec[base + val] = 1.0
    return vec


def encode_output(bx, by, py, gs, vx, vy):
    vec = [0.0] * OUTPUT_SIZE
    for idx, (val, size, base) in enumerate([
        (bx, BALL_X_RANGE, O_BALL_X),
        (by, BALL_Y_RANGE, O_BALL_Y),
        (py, PADDLE_Y_RANGE, O_PADDLE_Y),
        (gs, GAME_STATE_RANGE, O_GAME_STATE),
        (vx, BALL_V_RANGE, O_BALL_VX),
        (vy, BALL_V_RANGE, O_BALL_VY),
    ]):
        vec[base + val] = 1.0
    return vec


def decode_output(vec):
    bx = argmax(vec[O_BALL_X:O_BALL_X + BALL_X_RANGE])
    by = argmax(vec[O_BALL_Y:O_BALL_Y + BALL_Y_RANGE])
    py = argmax(vec[O_PADDLE_Y:O_PADDLE_Y + PADDLE_Y_RANGE])
    gs = argmax(vec[O_GAME_STATE:O_GAME_STATE + GAME_STATE_RANGE])
    vx = argmax(vec[O_BALL_VX:O_BALL_VX + BALL_V_RANGE])
    vy = argmax(vec[O_BALL_VY:O_BALL_VY + BALL_V_RANGE])
    return bx, by, vx, vy, py, gs


def squash_physics(bx, by, vx, vy, py, gs, ku, kd):
    """Paddle-ball collision physics: ball bounces off paddle (not left wall),
    off right/top/bottom walls. Loss only on paddle miss.
    Returns (bx, by, vx, vy, py, gs)."""
    if gs == 1:
        return bx, by, vx, vy, py, gs

    nbx = bx + (1 if vx == 1 else -1)
    nby = by + (1 if vy == 1 else -1)
    nvx, nvy = vx, vy
    npy = py
    ngs = gs

    # Top wall bounce
    if nby < 0:
        nby = 0
        nvy = 1  # now moving down

    # Bottom wall bounce
    if nby >= BALL_Y_RANGE:
        nby = BALL_Y_RANGE - 1
        nvy = 0  # now moving up

    # Right wall bounce (ball stays in play)
    if nbx >= BALL_X_RANGE:
        nbx = BALL_X_RANGE - 1
        nvx = 0  # now moving left

    # Left edge: paddle check — ball bounces off paddle OR game over
    if nbx < 0:
        # Ball rows [by, by+1], paddle rows [py, py+PADDLE_HEIGHT-1] = [py, py+4]
        # Overlap: ball_top <= paddle_bottom AND ball_bottom >= paddle_top
        if by <= py + 4 and by + 1 >= py:
            nbx = 0
            nvx = 1  # bounce right
            # Adjust vy based on where ball hits paddle
            # py+2 = paddle center; by < center → top half → up, by > center → lower half → down
            if by < py + 2:
                nvy = 0  # up
            elif by > py + 2:
                nvy = 1  # down
            # by == py+2: center → keep original vy
        else:
            # Paddle miss → game over
            nbx = 0
            ngs = 1

    # Paddle movement
    if ku:
        npy = max(0, py - 2)
    if kd:
        npy = min(PADDLE_Y_RANGE - 1, py + 2)

    return nbx, nby, nvx, nvy, npy, ngs


def generate_all_game_state_samples():
    """Yield (input_one_hot, output_one_hot) for every state combination."""
    for bx in range(BALL_X_RANGE):
        for by in range(BALL_Y_RANGE):
            for vx in range(BALL_V_RANGE):
                for vy in range(BALL_V_RANGE):
                    for py in range(PADDLE_Y_RANGE):
                        for gs in range(GAME_STATE_RANGE):
                            for ku in range(KEY_RANGE):
                                for kd in range(KEY_RANGE):
                                    inp = encode_input(bx, by, vx, vy, py, gs, ku, kd)
                                    nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
                                    out = encode_output(nbx, nby, npy, ngs, nvx, nvy)
                                    yield inp, out


def sample_game_state_batch(rng, count):
    """Generate a random batch of (input, output) pairs."""
    import random
    batch_in, batch_out = [], []
    for _ in range(count):
        bx = rng.randint(0, BALL_X_RANGE - 1)
        by = rng.randint(0, BALL_Y_RANGE - 1)
        vx = rng.randint(0, BALL_V_RANGE - 1)
        vy = rng.randint(0, BALL_V_RANGE - 1)
        py = rng.randint(0, PADDLE_Y_RANGE - 1)
        gs = rng.randint(0, GAME_STATE_RANGE - 1)
        ku = rng.randint(0, KEY_RANGE - 1)
        kd = rng.randint(0, KEY_RANGE - 1)
        inp = encode_input(bx, by, vx, vy, py, gs, ku, kd)
        nbx, nby, nvx, nvy, npy, ngs = squash_physics(bx, by, vx, vy, py, gs, ku, kd)
        out = encode_output(nbx, nby, npy, ngs, nvx, nvy)
        batch_in.append(inp)
        batch_out.append(out)
    return batch_in, batch_out
