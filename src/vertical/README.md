# Legacy Font Awesome bitmap catalog

These headers are the original Font Awesome bitmap catalog and are retained for
source compatibility with `<fontawesome.h>`. They are not the uIcons public API
and are intentionally excluded from formatting and static-analysis checks.

New projects should select only the required icons with the repository-local
CLI and include the generated header instead:

```sh
./scripts/uicons add fas/heart --manifest uicons.json
./scripts/uicons build --manifest uicons.json
```

The catalog is consumed as a pinned, checked-in source by the deterministic
uIcons generator. Provider-specific names stay inside the catalog/generator
boundary; runtime code uses `uicons::Icon` and `uicons::PixelFormat`.
