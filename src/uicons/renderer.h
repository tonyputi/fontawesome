#pragma once

#include <stdint.h>

#include <uicons/icon.h>

namespace uicons {

struct Canvas {
    void* context;
    uint16_t width;
    uint16_t height;
    void (*setPixel)(void* context, int16_t x, int16_t y, uint32_t color);

    constexpr Canvas(void* context_, uint16_t width_, uint16_t height_,
                     void (*setPixel_)(void*, int16_t, int16_t, uint32_t))
        : context(context_), width(width_), height(height_), setPixel(setPixel_) {}
};

namespace detail {

inline bool validIcon(const Icon& icon) {
    if (icon.data == nullptr || icon.width == 0 || icon.height == 0 || icon.stride == 0) {
        return false;
    }

    uint32_t expectedBytes = 0;
    switch (icon.format) {
    case PixelFormat::MonoRowMajor:
        if (icon.stride < static_cast<uint16_t>((icon.width + 7u) / 8u)) {
            return false;
        }
        expectedBytes = static_cast<uint32_t>(icon.stride) * icon.height;
        break;
    case PixelFormat::MonoVertical:
        if (icon.stride < icon.width) {
            return false;
        }
        expectedBytes =
            static_cast<uint32_t>(icon.stride) * ((static_cast<uint32_t>(icon.height) + 7u) / 8u);
        break;
    case PixelFormat::Gray2:
    case PixelFormat::Gray4:
        return false;
    }

    return icon.byteCount >= expectedBytes;
}

inline bool inside(const Canvas& canvas, int32_t x, int32_t y) {
    return x >= 0 && y >= 0 && x < canvas.width && y < canvas.height;
}

inline bool pixel(const Icon& icon, uint16_t x, uint16_t y) {
    uint32_t index = 0;
    uint8_t mask = 0;

    if (icon.format == PixelFormat::MonoRowMajor) {
        index = static_cast<uint32_t>(y) * icon.stride + (x / 8u);
        mask = static_cast<uint8_t>(0x80u >> (x % 8u));
    } else {
        index = static_cast<uint32_t>(y / 8u) * icon.stride + x;
        mask = static_cast<uint8_t>(1u << (y % 8u));
    }

    return (readByte(icon.data + index) & mask) != 0;
}

} // namespace detail

// Render an icon through a display-independent pixel sink. The sink is only
// called for set pixels and is never called outside the canvas bounds.
inline bool render(const Icon& icon, const Canvas& canvas, int16_t x, int16_t y,
                   uint32_t color = 1) {
    if (canvas.context == nullptr || canvas.setPixel == nullptr || canvas.width == 0 ||
        canvas.height == 0 || !detail::validIcon(icon)) {
        return false;
    }

    for (uint16_t iconY = 0; iconY < icon.height; ++iconY) {
        for (uint16_t iconX = 0; iconX < icon.width; ++iconX) {
            if (!detail::pixel(icon, iconX, iconY)) {
                continue;
            }

            const int32_t targetX = static_cast<int32_t>(x) + iconX;
            const int32_t targetY = static_cast<int32_t>(y) + iconY;
            if (detail::inside(canvas, targetX, targetY)) {
                canvas.setPixel(canvas.context, static_cast<int16_t>(targetX),
                                static_cast<int16_t>(targetY), color);
            }
        }
    }

    return true;
}

} // namespace uicons
