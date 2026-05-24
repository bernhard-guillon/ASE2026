"""
Reference squash renderer: draws ball, paddle, walls onto 20×15 grid.
"""
import math

W = 20
H = 15
OUTPUT_PIXELS = W * H  # 300

# Input layout (matches first 48 of the 56-input vector from squash_physics)
BALL_X_RANGE = 20
BALL_Y_RANGE = 15
PADDLE_Y_RANGE = 11
GAME_STATE_RANGE = 2

INPUT_SIZE = BALL_X_RANGE + BALL_Y_RANGE + PADDLE_Y_RANGE + GAME_STATE_RANGE  # 48

I_BALL_X = 0
I_BALL_Y = I_BALL_X + BALL_X_RANGE
I_PADDLE_Y = I_BALL_Y + BALL_Y_RANGE
I_GAME_STATE = I_PADDLE_Y + PADDLE_Y_RANGE

PADDLE_HEIGHT = 5
PADDLE_WIDTH = 3


def one_hot(index, size):
    vec = [0.0] * size
    vec[index] = 1.0
    return vec


def argmax(vec):
    return max(range(len(vec)), key=lambda i: vec[i])


def _render_frame(bx, by, py, gs):
    """Render a 20×15 frame. Returns list of 300 floats in [0,1]."""
    pixels = [0.0] * OUTPUT_PIXELS

    if gs == 1:
        # Game over: draw big X pattern
        for i in range(OUTPUT_PIXELS):
            x = i % W
            y = i // W
            if abs(x - y) <= 1 or abs(x - (H - 1 - y)) <= 1:
                pixels[i] = 1.0
        return pixels

    def set_px(x, y):
        if 0 <= x < W and 0 <= y < H:
            pixels[y * W + x] = 1.0

    # Walls (1-pixel thick)
    for y in range(H):
        set_px(0, y)       # left
        set_px(W - 1, y)   # right
    for x in range(W):
        set_px(x, 0)       # top
        set_px(x, H - 1)   # bottom

    # Paddle (at x=1)
    for dy in range(PADDLE_HEIGHT):
        for dx in range(PADDLE_WIDTH):
            set_px(1 + dx, py + dy)

    # Ball (2×2)
    set_px(bx, by)
    set_px(bx + 1, by)
    set_px(bx, by + 1)
    set_px(bx + 1, by + 1)

    return pixels


def render(bx, by, py, gs):
    return _render_frame(bx, by, py, gs)


def decode_input(vec):
    bx = argmax(vec[I_BALL_X:I_BALL_X + BALL_X_RANGE])
    by = argmax(vec[I_BALL_Y:I_BALL_Y + BALL_Y_RANGE])
    py = argmax(vec[I_PADDLE_Y:I_PADDLE_Y + PADDLE_Y_RANGE])
    gs = argmax(vec[I_GAME_STATE:I_GAME_STATE + GAME_STATE_RANGE])
    return bx, by, py, gs


def render_from_onehot(vec):
    bx, by, py, gs = decode_input(vec)
    return render(bx, by, py, gs)


def generate_all_renderer_samples():
    """Yield (input_one_hot, output_pixels) for every state combination."""
    for bx in range(BALL_X_RANGE):
        for by in range(BALL_Y_RANGE):
            for py in range(PADDLE_Y_RANGE):
                for gs in range(GAME_STATE_RANGE):
                    inp = [0.0] * INPUT_SIZE
                    inp[I_BALL_X + bx] = 1.0
                    inp[I_BALL_Y + by] = 1.0
                    inp[I_PADDLE_Y + py] = 1.0
                    inp[I_GAME_STATE + gs] = 1.0
                    pixels = render(bx, by, py, gs)
                    yield inp, pixels
