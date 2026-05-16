#!/usr/bin/env python3
"""
Throwaway terminal prototype for single-player squash on a 20x20 grid.

Controls:
- Up / Down arrows (or w / s): move paddle by one cell
- p: save ASCII screenshot
- r: reset game
- space: pause/resume
- q: quit
"""

from __future__ import annotations

import argparse
import curses
import random
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SquashGame:
    width: int = 20
    height: int = 20
    paddle_height: int = 3
    paddle_x: int = 19
    tick_ms: int = 120
    seed: int | None = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.screenshot_count = 0
        self.reset()

    @property
    def tick_seconds(self) -> float:
        return self.tick_ms / 1000.0

    def _random_launch_direction(self) -> tuple[int, int]:
        # Ball always launches to the right from x=0.
        return (1, self.rng.choice([-1, 0, 1]))

    def reset(self) -> None:
        self.ball_x = 0
        self.ball_y = self.height // 2
        self.ball_dx, self.ball_dy = self._random_launch_direction()
        self.paddle_top = (self.height // 2) - (self.paddle_height // 2)
        self.ticks = 0
        self.game_over = False

    def move_paddle(self, action: int) -> None:
        if action < 0:
            self.paddle_top -= 1
        elif action > 0:
            self.paddle_top += 1
        self.paddle_top = max(0, min(self.height - self.paddle_height, self.paddle_top))

    def step(self, action: int = 0) -> None:
        if self.game_over:
            return

        # Paddle may move only one cell per game tick.
        self.move_paddle(action)

        next_x = self.ball_x + self.ball_dx
        next_y = self.ball_y + self.ball_dy

        # Top/bottom wall reflection.
        if next_y < 0 or next_y >= self.height:
            self.ball_dy *= -1
            next_y = self.ball_y + self.ball_dy

        # Left wall reflection.
        if next_x < 0:
            self.ball_dx = 1
            next_x = self.ball_x + self.ball_dx

        # Right boundary: paddle collision or loss.
        if next_x >= self.paddle_x:
            if self.paddle_top <= next_y < self.paddle_top + self.paddle_height:
                self.ball_dx = -1
                next_x = self.ball_x + self.ball_dx
            else:
                self.ball_x = self.paddle_x
                self.ball_y = max(0, min(self.height - 1, next_y))
                self.game_over = True
                return

        self.ball_x = next_x
        self.ball_y = next_y
        self.ticks += 1

    def board_lines(self) -> list[str]:
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]

        for y in range(self.paddle_top, self.paddle_top + self.paddle_height):
            grid[y][self.paddle_x] = "#"
        grid[self.ball_y][self.ball_x] = "#"

        border = "+" + ("-" * self.width) + "+"
        lines = [border]
        lines.extend("|" + "".join(row) + "|" for row in grid)
        lines.append(border)
        return lines

    def save_screenshot(self, output_dir: str) -> Path:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_count += 1
        out_path = out_dir / f"squash_tick_{self.ticks:05d}_{self.screenshot_count:03d}.txt"
        header = (
            f"tick={self.ticks} ball=({self.ball_x},{self.ball_y}) "
            f"dir=({self.ball_dx},{self.ball_dy}) paddle_top={self.paddle_top} "
            f"game_over={self.game_over}"
        )
        out_path.write_text(header + "\n" + "\n".join(self.board_lines()) + "\n", encoding="utf-8")
        return out_path


def _action_from_script_char(ch: str) -> int:
    if ch in ("u", "U"):
        return -1
    if ch in ("d", "D"):
        return 1
    return 0


def run_headless(game: SquashGame, ticks: int, script: str, screenshot_dir: str) -> int:
    for i in range(ticks):
        action = _action_from_script_char(script[i]) if i < len(script) else 0
        game.step(action)
        if game.game_over:
            break
    shot = game.save_screenshot(screenshot_dir)
    print(
        f"Headless run complete: ticks={game.ticks}, game_over={game.game_over}, "
        f"ball=({game.ball_x},{game.ball_y}), screenshot={shot}"
    )
    return 0


def run_interactive(game: SquashGame, screenshot_dir: str) -> int:
    def _draw(stdscr: curses.window, paused: bool, status_msg: str) -> None:
        max_y, max_x = stdscr.getmaxyx()

        def _safe_addstr(row: int, text: str) -> None:
            if row < 0 or row >= max_y:
                return
            if max_x <= 1:
                return
            clipped = text[: max_x - 1]
            if not clipped:
                return
            try:
                stdscr.addstr(row, 0, clipped)
            except curses.error:
                # Some terminals still raise on boundary writes; treat as non-fatal.
                return

        stdscr.erase()
        lines = game.board_lines()
        for i, line in enumerate(lines):
            _safe_addstr(i, line)

        y0 = len(lines) + 1
        _safe_addstr(
            y0,
            (
                f"tick={game.ticks}  ball=({game.ball_x},{game.ball_y})  "
                f"dir=({game.ball_dx},{game.ball_dy})  paddle_top={game.paddle_top}  "
                f"{'GAME OVER' if game.game_over else 'RUNNING'}"
            ),
        )
        _safe_addstr(y0 + 1, "Controls: ↑/↓ or w/s move | p screenshot | r reset | space pause | q quit")
        _safe_addstr(y0 + 2, f"Paused: {paused}")
        if status_msg:
            _safe_addstr(y0 + 3, status_msg)
        stdscr.refresh()

    def _main(stdscr: curses.window) -> int:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(True)
        stdscr.keypad(True)

        paused = False
        status_msg = ""
        pending_action = 0
        next_tick = time.monotonic() + game.tick_seconds

        while True:
            key = stdscr.getch()
            while key != -1:
                if key in (ord("q"), ord("Q")):
                    return 0
                if key in (curses.KEY_UP, ord("w"), ord("W")):
                    pending_action = -1
                elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
                    pending_action = 1
                elif key == ord(" "):
                    paused = not paused
                elif key in (ord("r"), ord("R")):
                    game.reset()
                    paused = False
                    pending_action = 0
                    status_msg = "Game reset."
                elif key in (ord("p"), ord("P")):
                    shot = game.save_screenshot(screenshot_dir)
                    status_msg = f"Saved screenshot: {shot}"
                key = stdscr.getch()

            now = time.monotonic()
            if now >= next_tick:
                if not paused and not game.game_over:
                    game.step(pending_action)
                    pending_action = 0
                next_tick = now + game.tick_seconds

            _draw(stdscr, paused, status_msg)
            time.sleep(0.01)

    return curses.wrapper(_main)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Throwaway terminal squash prototype")
    parser.add_argument("--tick-ms", type=int, default=120, help="Tick duration in milliseconds")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for initial launch direction")
    parser.add_argument(
        "--screenshot-dir",
        default="screenshots",
        help="Directory where ASCII screenshots are written",
    )
    parser.add_argument(
        "--headless-ticks",
        type=int,
        default=0,
        help="Run without curses for N ticks (useful for quick checks)",
    )
    parser.add_argument(
        "--script",
        default="",
        help="Headless action script (u=up, d=down, any other char=stay)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    game = SquashGame(tick_ms=args.tick_ms, seed=args.seed)
    if args.headless_ticks > 0:
        return run_headless(game, args.headless_ticks, args.script, args.screenshot_dir)
    return run_interactive(game, args.screenshot_dir)


if __name__ == "__main__":
    raise SystemExit(main())
