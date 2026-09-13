# uIcons product differentiation

This document defines what uIcons is, what it is not, and the minimum viable
workflow. It is the working answer to issue #14.

## Target user

uIcons is for PlatformIO/Arduino firmware developers who:

- need a small number of icons on a constrained MCU;
- use monochrome, grayscale-capable, page-oriented, or framebuffer displays;
- want reproducible offline builds without Inkscape, ImageMagick, font
  rasterizers, or network access;
- do not want to be locked into one display library or one icon provider.

## Minimum viable workflow

The MVP is a selective build-time pipeline, not an icon collection:

```sh
./scripts/uicons init
./scripts/uicons add fas/heart fab/github --sizes 16
./scripts/uicons build
./scripts/uicons report --manifest uicons.json
```

Expected result:

- only the requested icons/sizes are emitted;
- output is written to `include/uicons/generated/uicons_generated.h`;
- the same icons render through `uicons::Icon`, `uicons::render`, and the
  existing display adapters;
- `report` shows the flash cost before flashing;
- host tests and `./scripts/quality.sh` validate generation and rendering
  without hardware.

End-to-end selective-generation examples:

- `examples/uicons.json` — Font Awesome selection;
- `examples/lucide.json` — Lucide selection.

## Comparison

| Existing option | Selection model | Provider/display coupling | uIcons relationship |
| --- | --- | --- | --- |
| `roo_icons` / `roo_display` | large Material collection | tied to its display ecosystem | uIcons stays display-independent and emits only selected assets; it does not build another display stack. |
| `Irisoled` | small PROGMEM bitmap set | focused set with non-blocking animation | uIcons adds multi-provider selective generation and measured footprint; animation remains separate work in #8. |
| `arduino-oled-icons` | fixed 16x16 OLED set | fixed set and target assumption | uIcons replaces fixed sets with manifest-selected catalogs, sizes, and formats. |
| `lv_font_conv` | selective Font Awesome glyph conversion | LVGL font pipeline | uIcons emits provider-neutral C++ bitmaps for any `Canvas` sink; it does not implement an LVGL font path. |
| `IconFontCppHeaders` | font headers including Font Awesome/Lucide | header distribution model | uIcons generates only requested icons/sizes deterministically, with version/license provenance and a renderer boundary. |
| U8g2 / Adafruit GFX bitmap APIs | application-supplied bitmaps | display libraries and drivers | uIcons feeds these libraries through adapters; it does not duplicate drivers, schedulers, or GUI toolkits. |

## Explicit non-goals

- No display drivers.
- No application scheduler ownership; no renderer may call `delay()`.
- No runtime SVG or font parser on device.
- No full-catalog distribution path.
- No naive resampling to unsupported sizes.
- No animation engine in the MVP; animation is tracked separately in #8.
- No new icon design language; catalogs are curated vendor packs with pinned
  versions and licenses.

## Feature acceptance filter

A new uIcons feature is accepted only if it preserves all of the following:

1. selective-only default: no unused icons in the default path;
2. deterministic offline generation with only the Python standard library;
3. provider-neutral core API;
4. display independence through the existing renderer boundary;
5. measurable footprint and host-side validation.

Anything that merely duplicates U8g2, Adafruit GFX, LVGL, or an existing icon
pack is rejected.

## Evidence

- Selective generation: `tools/uicons/`, `examples/uicons.json`,
  `examples/lucide.json`.
- Footprint evidence: `docs/footprint.md`, `./scripts/uicons report`.
- Licensing and provenance: `assets/LICENSE.txt`, `assets/lucide/`.
- Host validation and CI: `tests/`, `./scripts/quality.sh`,
  `.github/workflows/quality.yml`.
