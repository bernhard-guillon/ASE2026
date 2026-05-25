/* Pure C reference squash game — same physics & rendering as the neural model */

#define FRAMEBUFFER  ((volatile unsigned char *)0x20000)
#define DONE_FLAG    ((volatile unsigned int *)0x154000)
#define FB_STRIDE    320
#define FB_W         20
#define FB_H         15
#define PADDLE_H     5
#define PADDLE_W     3
#define PADDLE_MAX   10  /* PADDLE_Y_RANGE - 1 = 10 */

static int ball_x, ball_y, paddle_y, game_state, ball_vx, ball_vy;

static void set_px(int x, int y, unsigned char v) {
    if (x >= 0 && x < FB_W && y >= 0 && y < FB_H)
        FRAMEBUFFER[y * FB_STRIDE + x] = v;
}

static void render(void) {
    int x, y;
    for (y = 0; y < FB_H; y++)
        for (x = 0; x < FB_W; x++)
            FRAMEBUFFER[y * FB_STRIDE + x] = 0;

    if (game_state) {
        /* Big X on loss */
        for (y = 0; y < FB_H; y++)
            for (x = 0; x < FB_W; x++) {
                int d1 = x - y;
                int d2 = x - (FB_H - 1 - y);
                if ((d1 >= -1 && d1 <= 1) || (d2 >= -1 && d2 <= 1))
                    FRAMEBUFFER[y * FB_STRIDE + x] = 255;
            }
        return;
    }

    /* Walls */
    for (x = 0; x < FB_W; x++) {
        FRAMEBUFFER[0 * FB_STRIDE + x] = 255;
        FRAMEBUFFER[(FB_H-1) * FB_STRIDE + x] = 255;
    }
    for (y = 0; y < FB_H; y++) {
        FRAMEBUFFER[y * FB_STRIDE + 0] = 255;
        FRAMEBUFFER[y * FB_STRIDE + (FB_W-1)] = 255;
    }

    /* Paddle: x=1..3, y=paddle_y..paddle_y+4 */
    {
        int px, py2;
        for (px = 0; px < PADDLE_W; px++)
            for (py2 = 0; py2 < PADDLE_H; py2++)
                set_px(1 + px, paddle_y + py2, 255);
    }

    /* Ball: 2x2 */
    set_px(ball_x,     ball_y,     255);
    set_px(ball_x + 1, ball_y,     255);
    set_px(ball_x,     ball_y + 1, 255);
    set_px(ball_x + 1, ball_y + 1, 255);
}

static void step_key(int key) {
    if (game_state) return;

    /* key_up = 'w'/'W' → paddle -= 2 (max 0); key_down = 's'/'S' → paddle += 2 (max 10) */
    if (key == 'w' || key == 'W') {
        if (paddle_y >= 2) paddle_y -= 2; else paddle_y = 0;
    }
    if (key == 's' || key == 'S') {
        if (paddle_y <= PADDLE_MAX - 2) paddle_y += 2; else paddle_y = PADDLE_MAX;
    }

    /* Move ball */
    ball_x += (ball_vx ? 1 : -1);
    ball_y += (ball_vy ? 1 : -1);

    /* Top wall bounce */
    if (ball_y < 0)    { ball_y = 0;    ball_vy = 1; }
    /* Bottom wall bounce */
    if (ball_y >= FB_H){ ball_y = FB_H-1; ball_vy = 0; }
    /* Right wall bounce (ball stays in play) */
    if (ball_x >= FB_W){ ball_x = FB_W-1; ball_vx = 0; }
    /* Left edge: paddle check */
    if (ball_x < 0) {
        /* Ball rows [ball_y, ball_y+1], paddle rows [paddle_y, paddle_y+4] */
        if (ball_y <= paddle_y + 4 && ball_y + 1 >= paddle_y) {
            ball_x = 0;
            ball_vx = 1;
            /* Adjust vy based on where ball hits paddle */
            if (ball_y < paddle_y + 2)
                ball_vy = 0;  /* upper half → up */
            else if (ball_y > paddle_y + 2)
                ball_vy = 1;  /* lower half → down */
            /* center → keep vy */
        } else {
            ball_x = 0;
            game_state = 1;
        }
    }
}

void main(void) {
    int key;
    /* Read key ONCE at startup (a0 set by emulator via --char-code / --gui key injection) */
    __asm__ volatile ("mv %0, a0" : "=r"(key));
    /* Initial state matches neural model */
    ball_x = 0; ball_y = 0; paddle_y = 0; game_state = 0; ball_vx = 1; ball_vy = 0;

    for (;;) {
        render();
        step_key(key);
        *DONE_FLAG = 1;
    }
}

__attribute__((naked)) void _start(void) {
    __asm__ volatile (
        "lui sp, 0x20\n"
        "jal ra, main\n"
    );
}
