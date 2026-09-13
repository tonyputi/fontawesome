#pragma once

#include <stdint.h>

#include <uicons/renderer.h>

namespace uicons {
namespace adapters {

// Caller-owned 1-bpp page buffer. A page contains eight vertical pixels and
// stride bytes; this is the layout used by many monochrome OLED controllers.
struct MonoPages {
    uint8_t* data;
    uint16_t width;
    uint16_t height;
    uint16_t stride;

    constexpr MonoPages(uint8_t* data_, uint16_t width_, uint16_t height_, uint16_t stride_)
        : data(data_), width(width_), height(height_), stride(stride_) {}
};

namespace detail {

inline void setPagePixel(void* context, int16_t x, int16_t y, uint32_t color) {
    MonoPages& pages = *static_cast<MonoPages*>(context);
    const uint32_t page = static_cast<uint16_t>(y) / 8u;
    const uint32_t index = page * pages.stride + static_cast<uint16_t>(x);
    const uint8_t mask = static_cast<uint8_t>(1u << (y % 8));

    if (color != 0) {
        pages.data[index] |= mask;
    } else {
        pages.data[index] &= static_cast<uint8_t>(~mask);
    }
}

} // namespace detail

inline bool render(const Icon& icon, MonoPages& pages, int16_t x, int16_t y, uint32_t color = 1) {
    const uint16_t pageCount = static_cast<uint16_t>((pages.height + 7u) / 8u);
    if (pages.data == nullptr || pages.stride < pages.width || pages.width == 0 ||
        pages.height == 0 || pageCount == 0) {
        return false;
    }

    const Canvas canvas(&pages, pages.width, pages.height, detail::setPagePixel);
    return uicons::render(icon, canvas, x, y, color);
}

} // namespace adapters
} // namespace uicons
