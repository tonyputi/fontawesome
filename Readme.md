# uIcons

Embedded bitmap icons for PlatformIO and Arduino projects.

> The repository is being migrated from its original Font Awesome-only layout.
> The current Font Awesome headers remain available for compatibility while the
> provider-independent uIcons API is introduced.

## Current status

- Font Awesome Solid, Regular, and Brands bitmap assets are still available.
- Legacy assets are available in 16x16, 32x32, and 64x64 sizes.
- The public `uicons` API defines icon metadata and storage formats.
- A pinned Lucide outline pack is available through the same generator and API.
- Product scope, non-goals, and the minimum viable workflow are defined in
  `docs/differentiation.md`.
- Display renderers, selective generation, and animations are
  planned as tracked work in [issue #1](https://github.com/tonyputi/uicons/issues/1).

## Include the public API

```cpp
#include <uicons.h>
```

The legacy Font Awesome umbrella header is still supported:

```cpp
#include <fontawesome.h>
```

## Selective generation

The repository-local generator uses only Python's standard library and the
checked-in bitmap catalog. It does not require Inkscape, ImageMagick, a font
rasterizer, or network access during normal builds:

```sh
./scripts/uicons init
./scripts/uicons add fas/heart fab/github --sizes 16
./scripts/uicons build
```

This writes the selected assets to `include/uicons/generated/uicons_generated.h`.
Aliases such as `solid/heart` are canonicalized to `fas/heart`; unsupported
icons and sizes fail with an actionable error. Removing an icon from `uicons.json`
and running `build` rewrites the header without that icon. See
`examples/uicons.json` for a manifest example.

## Lucide icon pack

Lucide is available as a second catalog through the same core API
(`uicons::Icon`, `uicons::PixelFormat::MonoVertical`, `uicons::render`).
The pack vendors pinned upstream SVGs and converts them offline with the
standard library only:

```sh
./scripts/uicons init --manifest uicons-lucide.json --catalog lucide --sizes 16,24
./scripts/uicons add lucide/heart lucide/house --manifest uicons-lucide.json
./scripts/uicons build --manifest uicons-lucide.json
```

Lucide icons are outline-based and carry no brand logos; brands remain
Font Awesome `fab` only. Size 16 is the minimum recommended raster, 24 is
preferred, and 8 is intentionally not offered (strokes collapse below a
readable threshold). Every generated header records the Lucide version and
ISC license. See `assets/lucide/README.md` and `examples/lucide.json`.

## Formats and footprint

The generator emits 1-bpp masks in `mono-vertical` (default, page-oriented
controllers) or `mono-rowmajor` (`Adafruit_GFX`-style row layout) via the
manifest `"format"` field; both cost the same flash for widths divisible
by 8 and render through the same `uicons::render`. Measure any selection
before flashing:

```sh
./scripts/uicons report --manifest uicons.json
```

See `docs/footprint.md` for the measured comparison (representative icons,
format costs, evaluated RLE/cropping, and selective vs full-catalog bytes).

## Animations

Pre-rendered frame animations play through a non-blocking player: the app
passes `now` (e.g. `millis()`) to `uicons::update`/`uicons::draw`, and
nothing calls `delay()` or owns the scheduler. Animations are generated only
when listed in the manifest `"animations"` array, and frames may only
reference already-selected icons and sizes:

```sh
./scripts/uicons build --manifest examples/animation.json
./scripts/uicons report --manifest examples/animation.json
```

See `docs/animations.md` and `examples/animation.json`.

## Development quality gate

The maintained C++ sources use `.clang-format`, `.clang-tidy`, and `cppcheck`.
Generated icon data under `src/vertical/` is deliberately excluded from these
checks. Run the complete local gate with:

```sh
./scripts/quality.sh
```

The GitHub Actions workflow runs the same single-job gate. It intentionally does
not use a board matrix: hardware compilation can be added later when it provides
more value than its CI cost.

## Makefile

A thin convenience wrapper delegates to the canonical scripts (`make help`
lists everything):

```sh
make quality   # full gate, same as ./scripts/quality.sh
make build     # build every examples/*.json manifest into build/<name>/
make report    # footprint report for every example manifest
make clean     # remove build/ output and Python caches
```

## License

The library code is MIT licensed. Bundled icon assets retain the licenses and
attribution requirements of their original catalogs; see `assets/LICENSE.txt`.
