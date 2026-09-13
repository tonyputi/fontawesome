# uIcons

Embedded bitmap icons for PlatformIO and Arduino projects.

> The repository is being migrated from its original Font Awesome-only layout.
> The current Font Awesome headers remain available for compatibility while the
> provider-independent uIcons API is introduced.

## Current status

- Font Awesome Solid, Regular, and Brands bitmap assets are still available.
- Legacy assets are available in 16x16, 32x32, and 64x64 sizes.
- The public `uicons` API defines icon metadata and storage formats.
- Display renderers, selective generation, Lucide assets, and animations are
  planned as tracked work in [issue #1](https://github.com/tonyputi/fontawesome/issues/1).

## Include the public API

```cpp
#include <uicons.h>
```

The legacy Font Awesome umbrella header is still supported:

```cpp
#include <fontawesome.h>
```

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

## License

The library code is MIT licensed. Bundled icon assets retain the licenses and
attribution requirements of their original catalogs; see `assets/LICENSE.txt`.
