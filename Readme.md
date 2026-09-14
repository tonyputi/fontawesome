# uIcons

[![quality](https://github.com/tonyputi/uicons/actions/workflows/quality.yml/badge.svg)](https://github.com/tonyputi/uicons/actions/workflows/quality.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Embedded bitmap icons without the bloat: declare the icons you use, generate
a tiny header, render on any display — from 32 bytes of flash per 16×16 icon.**

Full Font Awesome catalogs ship tens of kilobytes you never draw. uIcons flips
the model: a manifest lists exactly the icons and sizes your firmware needs,
an offline generator emits only those bytes, and a display-independent
renderer draws them through whatever graphics library you already use.

## 60-second quickstart

```sh
./scripts/uicons init
./scripts/uicons add fas/heart --sizes 16
./scripts/uicons build
./scripts/uicons report --manifest uicons.json
```

```cpp
#include <uicons.h>
#include <uicons_generated.h>

uint8_t buffer[32] = {0};
uicons::adapters::MonoPages pages(buffer, 16, 16, 16);
uicons::adapters::render(uicons::generated::fas_heart_16x16, pages, 0, 0);
```

That is the whole workflow: manifest → header → pixels. Generation needs only
Python's standard library — no Inkscape, ImageMagick, rasterizer, or network.

## Works with your display

uIcons never depends on a display library. Pick the wiring for the one you
already use; every path below compiles in CI (see `examples/`).

| Display library | Manifest format | Wiring | Cost |
|---|---|---|---|
| [Adafruit GFX](docs/displays.md#adafruit-gfx-examplesdisplay_adafruit) | `mono-rowmajor` | `drawBitmap` direct, zero glue | +0 bytes RAM |
| [U8g2](docs/displays.md#u8g2-examplesdisplay_u8g2) | any | `Canvas` → `drawPixel`, 5 lines | one call per pixel |
| [Tiny4kOLED](docs/displays.md#tiny4koled-examplesdisplay_tiny4koled) | `mono-vertical` | `oled.bitmap` window, zero copy | +0 bytes RAM |

Details, bit-order rationale, and copy-paste snippets: [`docs/displays.md`](docs/displays.md).

## Two catalogs, one API

Both catalogs render through the same `uicons::Icon` + `uicons::render`:

- **Font Awesome** (`fas` solid, `far` regular, `fab` brands) — checked-in
  masters at 16/32/64 px. Brands live here only.
- **Lucide** (pinned 1.39.0, ISC) — outline icons converted offline from
  vendored SVGs at 16 px (minimum) and 24 px (preferred). Strokes collapse
  below 16 px, so smaller sizes are refused instead of silently downscaled.

```sh
./scripts/uicons init --manifest uicons-lucide.json --catalog lucide --sizes 16,24
./scripts/uicons add lucide/heart lucide/house --manifest uicons-lucide.json
./scripts/uicons build --manifest uicons-lucide.json
```

Every generated header records its catalog provenance and license.

## Footprint, measured not promised

| icon | size | data bytes | lit px |
|---|---|---|---|
| fas/heart | 16×16 | 32 | 158 |
| fas/heart | 32×32 | 128 | 608 |
| fas/heart | 64×64 | 512 | 2443 |
| lucide/heart | 16×16 | 32 | 54 |
| lucide/house | 24×24 | 72 | 172 |

A 6-asset Font Awesome pack (heart + github at 16/32/64) costs **1344 data
bytes**; shipping the full 16 px catalog instead would cost **51552 bytes**.
`mono-rowmajor` costs identical bytes for widths divisible by 8 — format choice
is about display compatibility, not flash. Full numbers, per-target mapping
(AVR PROGMEM vs ARM unified flash), and evaluated-but-rejected compression:
[`docs/footprint.md`](docs/footprint.md).

## Non-blocking animations

Pre-rendered frame animations play through a player that never calls `delay()`
and never owns your scheduler — your app passes `now` (e.g. `millis()`):

```sh
./scripts/uicons build --manifest examples/animation.json
```

Frames reuse already-selected icon bitmaps, so animation adds metadata only,
no duplicate pixel data. See [`docs/animations.md`](docs/animations.md).

## Status

Shipped and gated: selective generation, Lucide pack, both pixel formats,
rotation, animations, display wiring, compilable examples, and multi-target CI
(native, AVR Uno, ESP32). What is still open lives in
[GitHub issues](https://github.com/tonyputi/uicons/issues): Arduino Library
Manager, generator-input separation, and the quality-gate wishlist. Scope and
non-goals: [`docs/differentiation.md`](docs/differentiation.md).

The legacy full-catalog header is still available for compatibility:

```cpp
#include <fontawesome.h>  // legacy: pulls every icon; new code uses <uicons.h>
```

## What ships vs what is dev-only

The package boundary is enforced by `library.json` (`export.exclude`) and
checked by the `package` gate phase:

- **Shipped runtime** (`src/uicons/`, `src/uicons.h`): hand-written,
  provider-neutral, linted and analyzed.
- **Shipped legacy** (`src/fontawesome.h`, `src/vertical/`): frozen bitmap
  blobs for `<fontawesome.h>` compatibility. They also serve as the pinned
  input of the Font Awesome generator catalog, so they must stay in `src/`
  (moving them would break legacy includes) and must never be hand-edited.
- **Dev-only, never shipped** (`tools/`, `assets/`, `tests/`, `scripts/`,
  `examples/*.json`): generator, sources, and checks.
- **User-generated, never committed to `src/`** (`uicons_generated.h`):
  produced by `./scripts/uicons build` from your manifest; examples check in
  their copy under `examples/*/include/` so CI can drift-check it.

## Development

Sources are held to `.clang-format`, `.clang-tidy`, and `cppcheck`; host,
golden, generator, and on-hardware-compile checks run in one gate:

```sh
make quality   # full gate (format, tests, drift, examples, analysis, package)
make examples  # build every PlatformIO example (basic native + display AVR)
make build     # build every examples/*.json manifest into build/<name>/
make report    # footprint report for every example manifest
```

## License

The library code is MIT licensed. Bundled icon assets retain the licenses and
attribution requirements of their original catalogs; see `assets/LICENSE.txt`.
