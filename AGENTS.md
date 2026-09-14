# AGENTS.md

Instructions for AI coding agents working on this repository. Humans: the
narrative docs live in `Readme.md` and `docs/`; this file is the operational
contract.

## What this repo is

uIcons: embedded 1-bpp bitmap icons for PlatformIO/Arduino. Provider-neutral
runtime (`uicons::Icon`, `uicons::render`) + an offline selective generator
(manifest in, tiny header out) + pinned icon catalogs. Three catalogs:
Font Awesome (filled masters, legacy), Lucide (outline, ISC), Heroicons
(outline, MIT). Brands exist only in Font Awesome `fab`.

## Workflow (mandatory)

1. Pick up a GitHub issue (`gh issue list --repo tonyputi/uicons --state open`).
2. `git switch main && git pull --ff-only origin main`, then
   `git switch -c <type>/<slug>` (`feat/`, `chore/`, `docs/`).
3. Implement, then run the gate: `./scripts/quality.sh` (exit 0 required).
   Iterate per phase while working:
   `./scripts/quality.sh [format|host|python|determinism|stale|examples|tidy|cppcheck|package]`
4. Push, open a PR with `gh api --method POST repos/tonyputi/uicons/pulls`,
   body ending in `Closes #<n>`. Never merge: merging is owner-level.
5. After the owner merges, `git switch main && git pull --ff-only`, delete
   the local branch.

Environment notes: `clang-format`/`clang-tidy` live under
`/opt/homebrew/opt/llvm/bin` on macOS (export PATH); `ruff==0.16.7`
(dev-only, never a runtime dep); `./scripts/uicons` runs on bare `python3`.

## Hard invariants (CI enforces all of these)

- **Generator is stdlib-only and offline.** No Pillow/numpy/click/pydantic or
  any third-party import in `tools/uicons` (`tests/test_uicons_stdlib.py`
  fails the build otherwise). No network, no rasterizer binaries.
- **Generation is byte-deterministic.** `determinism` builds every
  `examples/*.json` twice and `cmp`s; `stale` rebuilds every
  `examples/*/uicons.json` against its checked-in `include/` header.
- **Golden pins are exact.** `tests/golden/*.pbm` (C++) and hex pins in
  `tests/test_uicons_*.py` fail on a single changed pixel. Regenerate pins
  only by running the code, never by hand-editing expected values.
- **`src/vertical/` is frozen.** Dual role (legacy `<fontawesome.h>` payload
  + generator input); never hand-edit, never move (legacy includes resolve
  under `src/`). Changes arrive only as reviewed re-vendors.
- **Animations never block.** No `delay()`, no heap allocs in the player path,
  no scheduler ownership; time comes from the caller's `now` (wrap-safe ms).
- **Rotations are orthogonal only** (`Deg0/90/180/270`), zero extra RAM.
- **Display libraries are glue-only.** Adafruit/U8g2/Tiny4kOLED stay optional
  header glue + sketches; never hard deps in `library.json`.
- **Package boundary.** `library.json` `export.exclude` keeps dev files out;
  the `package` phase asserts both leaks AND must-ship files
  (`src/uicons.h`, `src/uicons/icon.h`, `src/fontawesome.h`,
  `src/vertical/`, `library.json`).
- **Makefile is a thin wrapper.** Every workflow has exactly one
  implementation in `scripts/`; `make` targets delegate, never duplicate
  (e.g. `make package` → `phase_package` via `UICONS_PACKAGE_OUTPUT`).
- **Single-job CI, no board matrix.** Budget-aware by design; smoke per
  family (native + AVR Uno + ESP32) inside the one `quality` job.

## Code conventions

- C++11, header-only where possible; `-Wall -Wextra -Wpedantic -Wconversion
  -Wshadow -Werror` on host tests; `.clang-format` (100 cols) is law.
- Python: `ruff check` (`E,F`, 100 cols, E501 exempted only for test data);
  `.python-version` is `3.12`.
- Catalog additions: new `*Catalog` class mirroring `LucideCatalog` plus a
  `<pack>.py` metadata module mirroring `heroicons.py` (`SIZES`, `ALIASES`,
  `SOURCE_URL`, `LICENSE_NAME`; bitmap-backed `fontawesome.py` carries
  families/aliases only, no `SIZES`/`read_pack_metadata`), one line
  in `CATALOGS`, vendored SVGs under `assets/<pack>/` with `VERSION` +
  `SOURCE.md` + license file (force-add: `assets/` is gitignored),
  `examples/<pack>.json` in the drift loop, MIT/ISC-class license only,
  attribution in `assets/LICENSE.txt`, catalog table in `Readme.md`.
- Only outline/stroke SVG packs reuse the pipeline in
  `tools/uicons/stroke.py`; fill-based styles need a new rasterizer (out of
  scope until requested).
- Filenames/identifiers: `family/name` (`fas/heart`, `lucide/house`,
  `heroicons/home`); aliases canonicalized in the catalog, never at runtime.
