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

## License

The library code is MIT licensed. Bundled icon assets retain the licenses and
attribution requirements of their original catalogs; see `assets/LICENSE.txt`.
