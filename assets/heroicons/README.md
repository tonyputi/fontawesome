# Heroicons icon pack

Vendored, pinned Heroicons outline sources converted offline to embedded
mono-vertical bitmaps by the shared stroke pipeline in
`tools/uicons/stroke.py` (Python standard library only).

- Pinned release: see `VERSION` (upstream `https://github.com/tailwindlabs/heroicons`)
- License: MIT, see `LICENSE-MIT.txt`
- Source pin details: see `SOURCE.md`

## Scope notes

- Only the **outline** style is vendored. Heroicons outlines are
  **stroke-based** on a 24x24 grid (1.5-unit strokes), so they reuse the same
  converter as Lucide. **Solid** icons are fill-based and intentionally out of
  scope: the offline converter paints strokes only.
- Heroicons **has no brand logos**. Brand icons remain available only through
  the Font Awesome `fab` family.
- This pack vendors a **curated subset** (`bars-3`, `bell`, `check`,
  `cog-6-tooth`, `heart`, `home`, `magnifying-glass`, `star`, `x-mark`).
  Extending it means copying the upstream SVG at the pinned tag and re-running
  the generator tests.

## Legibility

- `16` is the minimum recommended raster size; `24` (the native grid) is
  preferred for 1.5-unit stroke detail.
- Size `8` is intentionally not offered: thin outline strokes collapse below
  a readable threshold that small. Use the filled Font Awesome assets when an
  8-pixel glyph is required.

Every generated header carries the pack version and license, for example:

```cpp
// Source: Heroicons 2.2.0 (MIT, https://github.com/tailwindlabs/heroicons).
```

## Usage

```sh
./scripts/uicons init --manifest uicons-heroicons.json --catalog heroicons --sizes 16,24
./scripts/uicons add heroicons/heart heroicons/home --manifest uicons-heroicons.json
./scripts/uicons build --manifest uicons-heroicons.json
```
