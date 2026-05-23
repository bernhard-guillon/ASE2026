# future-me.md

Purpose: Handoff for another Hermes instance to continue fixing game-movement GUI behavior in emulator for game-movement model.

## User intent
- User wants game-movement model (`game-movement.elf`) to be testable interactively in emulator GUI.
- `--dump-framebuffer` path works and is accepted as baseline truth.
- `--gui` path currently looks wrong (ghost/random sparse points, controls seem ineffective).
- User asked us to fix it directly (no manual patch application preferred).

## Current environment constraints (critical)
- Repo path: `/home/nice/Uni/Master/ASE2026/ASE2026`
- Files are owned by `root:root`; agent runs as `hermes`.
- Direct edits fail with permission denied.
- No `sudo` command available in this runtime.

Observed permissions:
- `projects/emulator` owned by root
- `projects/emulator/emulator_runner.cpp` owned by root and not writable by hermes

## What was already investigated

### 1) Pipeline status
- `game-movement.elf` already exists and runs with `emulator_runner`.
- Artifacts present:
  - `projects/emulator/build/game-movement.elf`
  - `projects/emulator/build/game-movement.s`
  - `projects/emulator/build/game-movement.o`
  - `projects/emulator/build/game-movement_generator.json`
- Game-movement model artifacts exist in `projects/game-movement/src` including `squash_model.pth`, dataset, eval JSON.

### 2) Black-box behavior in non-GUI mode
Command used:
- `./projects/emulator/build/emulator_runner ./projects/emulator/build/game-movement.elf --char-code 106 --cycles 12000000 --dump-framebuffer`

Result:
- Return code 0
- Framebuffer dump has exactly 4 active cells (all 255), matching game-movement top-4 output mapping.

### 3) Inference cycle requirement measured
Binary-search measurement showed:
- first non-zero output around: **8,871,650 cycles**
- first full top-4 output around: **8,871,656 cycles**

Implication:
- Current GUI loop only running 10,000 steps/frame is far too low.

### 4) Root causes for bad GUI behavior
In `projects/emulator/emulator_runner.cpp`:
1. GUI loop compute chunk is too small (`10000`) for game-movement model.
2. GUI input mapping is generic; game-movement model expects `j`/`k`/`space` semantics.
3. GUI does not keep `a0` stable through long compute chunk in same robust way as `--char-code` path.
4. GUI starts from zeroed framebuffer; game-movement model expects game-like frame state. This causes odd sparse outputs initially.

## Agreed fix strategy
Implement in `emulator_runner.cpp`:

1) Add game-movement-aware GUI mode automatically for `game-movement` ELF.
2) Add `--gui-cycles <N>` CLI option.
3) Use large default GUI chunk for game-movement if not specified (e.g. `9000000`).
4) Keep current key code stable across compute chunk by repeatedly writing `a0` each step.
5) In game-movement GUI mode:
   - Map keys:
     - Up arrow / W -> `'j'`
     - Down arrow / S -> `'k'`
     - Space -> `' '`
   - Ignore unrelated keys.
6) Seed initial framebuffer before first render in game-movement mode:
   - ball at `(x=0, y=10)`
   - paddle at `x=19`, `y=9..11`

## Patch artifacts already generated
(These were written outside repo because repo is read-only for agent)
- `/opt/data/gui_squash_fix.patch` (timing/input/a0 fix)
- `/opt/data/gui_squash_full_fix.patch` (includes framebuffer seeding + all above)

Preferred: use `gui_squash_full_fix.patch` semantics.

## What blocked completion
- Could not apply patch due to root-owned repo and no sudo.
- User asked for direct fix (no manual patching), but permission block prevents action.

## Next-step instructions for takeover instance
1. Check if permissions changed. If writable, apply equivalent edits directly to:
   - `projects/emulator/emulator_runner.cpp`
2. Rebuild emulator target.
3. Validate with these tests:
   - Manual non-GUI baseline:
     - `./projects/emulator/build/emulator_runner ./projects/emulator/build/game-movement.elf --char-code 106 --cycles 12000000 --dump-framebuffer`
     - Ensure 4 active cells of 255.
   - GUI:
     - `./projects/emulator/build/emulator_runner ./projects/emulator/build/game-movement.elf --gui`
     - Confirm initial frame shows seeded ball+paddle pattern and controls work.
   - Optional tune:
     - `--gui-cycles 8872000`
4. If possible, add/adjust black-box test coverage for GUI game-movement mode key mapping + visible frame update.

## Communication style requested by user
- User prefers direct action over manual patch instructions.
- If blocked, explain briefly and ask for minimal unblock step.

## Current conversation state summary
- User last asked to “write our current strategy and state in future-me.md so another instance can take over.”
- This file is intended to satisfy that request and preserve continuity.
