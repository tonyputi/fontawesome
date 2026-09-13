# Lucide source pin

- Provider: Lucide (`https://lucide.dev`)
- Pinned release: `1.39.0` (see `VERSION`)
- Source tag: `https://github.com/lucide-icons/lucide/tree/1.39.0/icons`
- License: ISC (see `LICENSE-ISC.txt`)
- Curated subset: `bell`, `check`, `heart`, `house`, `menu`, `search`,
  `settings`, `star`, `x`

The SVGs in `icons/` are verbatim copies of the upstream files at the pinned
tag. They are converted to embedded mono-vertical bitmaps by the
dependency-free converter in `tools/uicons/lucide.py` using only the Python
standard library. No font rasterizer, image tool, or network access is needed
during normal builds.

Attribution is preserved in every generated header and in the PlatformIO
package metadata.
