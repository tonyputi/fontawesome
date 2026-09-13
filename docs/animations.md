# uIcons non-blocking animations

Pre-rendered frame animations with an explicit clock. The application owns
time and the screen; the player only maps `now` to a frame.

## Model

- `AnimationFrame { const Icon* icon; uint32_t durationMs; }` — one frame.
- `Animation { frames, frameCount, loopCount }` — `loopCount == 0` loops
  forever, otherwise the player stops on the last frame after `loopCount`
  loops. All data is `const` and typically lives in flash.
- `Player` — caller-owned RAM state (12 bytes on the host), one per
  on-screen animation. Frame bitmaps are shared between players.
- `start(player, animation, now)` begins playback; `update(player, animation,
  now)` advances it and returns true only when the visible frame changed, so
  the app can skip redraws; `draw(...)` advances and renders the current
  frame through the same `uicons::render`.
- Timestamps are `uint32_t` milliseconds (e.g. `millis()`). Elapsed time uses
  unsigned subtraction, so the counter may wrap around safely.
- Nothing calls `delay()`, allocates, throws, reads a clock, or owns the
  scheduler. Parametric animations (blink, pulse, spinner) are intentionally
  out of scope: compose them app-side from `update`/`draw`, or add explicit
  pre-rendered frames.

## Selecting animations

Animations are built only when listed in the manifest `"animations"` array.
Every frame must reference an icon already in manifest `"icons"` at a size
already in manifest `"sizes"` — animations never pull in hidden assets:

```json
{
  "catalog": "fontawesome",
  "sizes": [16],
  "format": "mono-vertical",
  "icons": ["fas/heart"],
  "animations": [
    {
      "name": "heartbeat",
      "loop": 0,
      "frames": [
        {"icon": "fas/heart", "size": 16, "duration_ms": 400},
        {"icon": "fas/heart", "size": 16, "duration_ms": 200}
      ]
    }
  ]
}
```

See `examples/animation.json`. The generator emits one `AnimationFrame`
array and one `Animation` per entry (symbols `anim_<name>`), deterministically
sorted by name; frames keep manifest order. Unknown icons, sizes outside the
manifest, non-positive durations, and duplicate names fail with actionable
errors. Removing an animation from the manifest removes its symbols on the
next `build`, and `report` lists per-animation frames and total duration.

## Application loop

```cpp
#include <uicons.h>
#include <uicons_generated.h>

uicons::Player heartbeat;

void setup() {
    uicons::start(heartbeat, uicons::generated::anim_heartbeat, millis());
}

void loop() {
    if (uicons::update(heartbeat, uicons::generated::anim_heartbeat, millis())) {
        redraw = true;  // only redraw on frame changes
    }
    if (redraw) {
        uicons::draw(heartbeat, uicons::generated::anim_heartbeat, canvas, x, y, millis());
        redraw = false;
    }
}
```

## Flash and timing costs

Measured on the host for a 2-frame `heartbeat` over one 16x16 icon
(`./scripts/uicons report`):

- icon bitmaps: 32 data bytes, shared with the static icon (frames add no
  bitmap cost when they reuse selected icons);
- frame table: 2 entries × `sizeof(AnimationFrame)` (16 bytes on the host:
  pointer + `uint32_t` + padding; exact layout is target-dependent);
- animation object: `sizeof(Animation)` (16 bytes on the host);
- player RAM: `sizeof(Player)` (12 bytes on the host), allocated by the app.

Frame timing is exact to the millisecond timestamp the app passes in; the
player itself adds no jitter beyond one `update` call per frame change. Frame
durations must be positive; an animation with no frames or zero total
duration refuses to `start`.
