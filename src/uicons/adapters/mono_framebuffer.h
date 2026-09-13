#pragma once

#include <stdint.h>

#include <uicons/renderer.h>

namespace uicons {
namespace adapters {

// Caller-owned 1-bpp row-major framebuffer. Pixels are MSB-first within a
// byte, making it suitable for a conventional host-side framebuffer.
struct MonoFramebuffer {
    uint8_t* data;
    uint16_t width;
    uint16_t height;
    uint16_t stride;

    constexpr MonoFramebuffer(uint8_t* data_,
                              uint16_t width_,
                              uint16_t height_,
                              uint16_t stride_)
        : data(data_), width(width_), height(height_), stride(stride_) {}
};

namespace detail {

inline void setFramebufferPixel(void* context,
                                int16_t x,
                                int16_t y,
                                uint32_t color) {
    MonoFramebuffer& framebuffer =
        *static_cast<MonoFramebuffer*>(context);
    const uint32_t index = static_cast<uint32_t>(y) * framebuffer.stride +
                           static_cast<uint16_t>(x) / 8u;
    const uint8_t mask = static_cast<uint8_t>(0x80u >> (x % 8));

    if (color != 0) {
        framebuffer.data[index] |= mask;
    } else {
        framebuffer.data[index] &= static_cast<uint8_t>(~mask);
    }
}

}  // namespace detail

inline bool render(const Icon& icon,
                   MonoFramebuffer& framebuffer,
                   int16_t x,
                   int16_t y,
                   uint32_t color = 1) {
    if (framebuffer.data == nullptr ||
        framebuffer.stride < static_cast<uint16_t>((framebuffer.width + 7u) / 8u)) {
        return false;
    }

    const Canvas canvas(&framebuffer,
                        framebuffer.width,
                        framebuffer.height,
                        detail::setFramebufferPixel);
    return uicons::render(icon, canvas, x, y, color);
}

}  // namespace adapters
}  // namespace uicons
