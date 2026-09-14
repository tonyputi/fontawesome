# Heroicons source pin

- Provider: Heroicons (`https://heroicons.com`)
- Pinned release: `v2.2.0` (see `VERSION`)
- Source tag: `https://github.com/tailwindlabs/heroicons/tree/v2.2.0/optimized/24/outline`
- License: MIT (see `LICENSE-MIT.txt`)
- Curated subset: `bars-3`, `bell`, `check`, `cog-6-tooth`, `heart`, `home`,
  `magnifying-glass`, `star`, `x-mark`

The SVGs in `icons/` are verbatim copies of the upstream files at the pinned
tag. Only the outline style is vendored: solid icons are fill-based and the
dependency-free converter only paints strokes. They are converted to embedded
mono-vertical bitmaps by the shared stroke pipeline in
`tools/uicons/lucide.py` using only the Python standard library. No font
rasterizer, image tool, or network access is needed during normal builds.

Attribution is preserved in every generated header and in the PlatformIO
package metadata.
