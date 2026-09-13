# Display wiring

uIcons never depends on a display library. The renderer draws through a
`Canvas` pixel sink, and each supported library has exactly one proven way to
receive icon bytes. Copy the snippet for your display; the matching sketch
under `examples/` compiles it.

| Library | Manifest format | Wiring | Flash-safe | Cost |
|---|---|---|---|---|
| Adafruit GFX | `mono-rowmajor` | `drawBitmap` direct, zero glue | yes (`pgm_read_byte` inside) | +0 bytes RAM |
| U8g2 | any | `Canvas` → `drawPixel`, 5 lines | yes (bytes read via `readByte`) | per-pixel call |
| Tiny4kOLED | `mono-vertical` | `oled.bitmap` window, zero copy | yes (`pgm_read_byte` inside) | +0 bytes RAM |

## Adafruit GFX (`examples/display_adafruit/`)

`mono-rowmajor` output is byte-identical to what `drawBitmap` expects:
scanline stride `(w + 7) / 8`, MSB-first, unset bits transparent, read through
`pgm_read_byte`:

```cpp
const uicons::Icon& heart = uicons::generated::fas_heart_16x16;
display.drawBitmap(x, y, heart.data, static_cast<int16_t>(heart.width),
                   static_cast<int16_t>(heart.height), SSD1306_WHITE);
```

No buffer, no conversion, no copy. Works on AVR (data stays in PROGMEM) and
on unified-address chips (where `pgm_read_byte` is a plain dereference).

## U8g2 (`examples/display_u8g2/`)

Do **not** use `drawXBM`: it expects XBM bit order (LSB-first per row) while
uIcons rows are MSB-first, so the icon would render mirrored. Draw per-pixel
through the renderer instead — this works in every U8g2 buffer mode, including
paged mode inside the `firstPage`/`nextPage` loop:

```cpp
void setU8g2Pixel(void* context, int16_t x, int16_t y, uint32_t color) {
    if (color != 0) {
        static_cast<U8G2*>(context)->drawPixel(static_cast<u8g2_uint_t>(x),
                                               static_cast<u8g2_uint_t>(y));
    }
}

u8g2.clearBuffer();
const uicons::Canvas canvas(&u8g2, 128, 64, setU8g2Pixel);
uicons::render(uicons::generated::fas_heart_16x16, canvas, 56, 24);
u8g2.sendBuffer();
```

## Tiny4kOLED (`examples/display_tiny4koled/`)

`oled.bitmap(x0, y0, x1, y1, data)` takes an SSD1306 page window — x in
pixels, y in 8-pixel pages — which is exactly the `mono-vertical` layout.
Page-aligned icons (`y % 8 == 0`, `height % 8 == 0`) blast straight from
flash with no RAM buffer:

```cpp
// 16x16 icon at pixel (56, 8): pages 1..2, 16 columns x 2 pages = 32 bytes.
const uicons::Icon& heart = uicons::generated::fas_heart_16x16;
oled.bitmap(56, 1, 56 + heart.width, 1 + heart.height / 8, heart.data);
```

`bitmap()` reads through `pgm_read_byte`, so PROGMEM data is safe on AVR.
For non-page-aligned placement, render into a `MonoPages` RAM buffer first
and send that buffer through the same window call.
