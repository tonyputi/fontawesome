# Lucide icon pack

Vendored, pinned Lucide sources converted offline to embedded mono-vertical
bitmaps by `tools/uicons/lucide.py` (Python standard library only).

- Pinned release: see `VERSION` (upstream `https://github.com/lucide-icons/lucide`)
- License: ISC, see `LICENSE-ISC.txt`
- Source pin details: see `SOURCE.md`

## Scope notes

- Lucide icons are **outline-based strokes** on a 24x24 grid. They complement
  the filled Font Awesome assets; they do not replace them.
- Lucide **has no brand logos**. Brand icons remain available only through the
  Font Awesome `fab` family.
- This pack vendors a **curated subset** (`bell`, `check`, `heart`, `house`,
  `menu`, `search`, `settings`, `star`, `x`). Extending it means copying the
  upstream SVG at the pinned tag and re-running the generator tests.
- `lucide/home` is accepted as an alias of `lucide/house` (Lucide renamed the
  icon; both spellings resolve to the same asset).

## Legibility

- `16` is the minimum recommended raster size; `24` (the native grid) is
  preferred for stroke detail such as the `settings` gear teeth.
- Size `8` is intentionally not offered: 2-unit Lucide strokes collapse below
  a readable threshold that small. Use the filled Font Awesome assets when an
  8-pixel glyph is required.

Every generated header carries the pack version and license, for example:

```cpp
// Source: Lucide 1.39.0 (ISC, https://github.com/lucide-icons/lucide).
```

## Usage

```sh
./scripts/uicons init --manifest uicons-lucide.json --catalog lucide --sizes 16,24
./scripts/uicons add lucide/heart lucide/house --manifest uicons-lucide.json
./scripts/uicons build --manifest uicons-lucide.json
```
