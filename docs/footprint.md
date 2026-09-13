# uIcons footprint and format comparison

All numbers below are produced by the dependency-free reporter — no hardware
needed to reproduce them:

```sh
./scripts/uicons report --manifest <manifest>
./scripts/uicons report --manifest <manifest> --as json
```

Flash cost on device is dominated by the `UICONS_PROGMEM` data arrays, whose
sizes are exact and platform-independent. Each icon additionally carries one
`const Icon` metadata object (`sizeof(Icon)` is 24 bytes on the host; the
exact placement and padding are target-dependent, and on AVR the data arrays
stay in flash through `PROGMEM` while object placement follows the toolchain
defaults). `header bytes` is the generated source file size, useful for
compile-time intuition but not a device cost.

## Target mapping

Data bytes are exact on every target because the generator emits the same
1-bpp arrays everywhere; only their placement differs:

- **AVR (Harvard architecture):** data arrays stay in flash through
  `UICONS_PROGMEM`; every byte is read through `readByte`, i.e.
  `pgm_read_byte`, which the golden tests cover on host. `Icon` metadata
  objects follow the toolchain defaults for `const` data.
- **ARM Cortex-M (unified address space):** `const` data and metadata live
  in flash with zero RAM cost; `UICONS_PROGMEM` is empty and `readByte` is a
  plain dereference.
- **Host:** `sizeof(Icon)` is 24 bytes; use it only as an upper-bound hint,
  since padding is target-dependent.

No hardware is needed to reproduce any number here: `./scripts/quality.sh`
rebuilds the example packs, checks the outputs byte-for-byte, and runs the
`report` command in CI.

## Representative icons (measured)

Font Awesome, `mono-vertical`:

| icon | size | bytes | lit px | density | crop bytes | RLE bytes |
| --- | --- | --- | --- | --- | --- | --- |
| fab/github | 16x16 | 32 | 116 | 0.453 | 32 | 48 |
| fab/github | 32x32 | 128 | 443 | 0.433 | 124 | 142 |
| fab/github | 64x64 | 512 | 1720 | 0.420 | 496 | 264 |
| fas/heart | 16x16 | 32 | 158 | 0.617 | 32 | 44 |
| fas/heart | 32x32 | 128 | 608 | 0.594 | 128 | 94 |
| fas/heart | 64x64 | 512 | 2443 | 0.596 | 448 | 196 |

Lucide, `mono-vertical`:

| icon | size | bytes | lit px | density | crop bytes | RLE bytes |
| --- | --- | --- | --- | --- | --- | --- |
| lucide/heart | 16x16 | 32 | 54 | 0.211 | 32 | 58 |
| lucide/heart | 24x24 | 72 | 128 | 0.222 | 72 | 130 |
| lucide/house | 16x16 | 32 | 96 | 0.375 | 32 | 60 |
| lucide/house | 24x24 | 72 | 172 | 0.299 | 72 | 122 |
| lucide/settings | 16x16 | 32 | 88 | 0.344 | 32 | 56 |
| lucide/settings | 24x24 | 72 | 184 | 0.319 | 72 | 124 |

A representative 6-icon Font Awesome pack (heart + github at 16/32/64) costs
**1344 data bytes**; the equivalent 6-asset Lucide pack (heart/house/settings
at 16/24) costs **312 data bytes** — outline strokes are cheaper than filled
shapes at the same raster size.

## Format comparison

`mono-rowmajor` produces **identical data byte counts** (1344 and 312 in the
packs above): for widths divisible by 8, `width * pages` equals
`height * row_bytes`. Format choice is therefore about display compatibility,
not flash:

- `mono-vertical` (default): column-major pages, LSB-first — the native layout
  for page-oriented controllers (SSD1306-style) and the existing adapters.
- `mono-rowmajor`: MSB-first rows — matches `Adafruit_GFX`-style
  `drawBitmap` expectations; the generated header sets
  `PixelFormat::MonoRowMajor` and the same `uicons::render` draws it
  (verified: row-major `fas/heart` renders the same 158 pixels).

## Evaluated and rejected as defaults

- **Byte-run RLE** (`(count, value)` pairs): loses at small sizes (e.g. 70 vs
  64 bytes for the 2-icon 16px pack, 550 vs 312 for Lucide) and only wins on
  large dense icons (460 vs 1024 at 64px). A decoder would add flash, RAM
  state, and per-icon timing variance. Reported for comparison; headers stay
  uncompressed so the renderer needs no decoder.
- **Bounding-box cropping**: saves ~6% here (1260 vs 1344) because catalog
  icons already fill their canvas, while requiring anchor metadata and
  complicating clipping. Reported as `crop bytes`; not emitted.
- **Naive resampling to new sizes**: rejected. Font Awesome ships checked-in
  masters only at 16/32/64; Lucide strokes collapse below 16px (see
  `assets/lucide/README.md`). Small icons must be checked masters, never
  silent downscales — hence per-catalog size validation with actionable
  errors. Small masters are visually checked, not just measured: the pack
golden test renders the real 16x16 `fas/heart` through the renderer and
compares it pixel-for-pixel against `tests/golden/fas-heart-16.pbm`, and
the Lucide suite enforces legibility density bounds at every supported size.
- **Per-icon headers plus linker garbage collection**: unnecessary. The
  single selective header already excludes every unused icon, so there is
  nothing left for the linker to collect; per-icon headers would only slow
  down builds with more translation units.
- **Grayscale formats**: deferred. Neither catalog ships grayscale masters,
  so generated output stays 1-bpp; `PixelFormat::Gray2`/`Gray4` remain
  reserved in the API and rejected by the renderer until a pack needs them.

## Selective generation is the default path

The full checked-in Font Awesome catalog holds 1611 icons per size:

| size | full catalog data | 2-icon selective pack |
| --- | --- | --- |
| 16 | 51552 bytes | 64 bytes |
| 32 | 206208 bytes | 256 bytes |
| 64 | 824832 bytes | 1024 bytes |

The generator only ever emits the manifest selection; there is no code path
that includes unused icons. The `report` command makes the saving visible
before flashing.
