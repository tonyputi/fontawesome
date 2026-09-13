#pragma once

#include <stdint.h>

#if defined(__AVR__)
#include <avr/pgmspace.h>
#endif

// Storage qualifier used by generated icon data. It is empty on host builds
// and on platforms where flash and data memory share the same address space.
// On microcontrollers PROGMEM is provided by the platform headers. It is
// intentionally not defined here to avoid leaking an Arduino macro into host
// applications; the legacy umbrella header provides a local fallback.
#if defined(PROGMEM)
#define UICONS_PROGMEM PROGMEM
#else
#define UICONS_PROGMEM
#endif

namespace uicons {

enum class PixelFormat : uint8_t {
    MonoRowMajor = 0,
    MonoVertical = 1,
    Gray2 = 2,
    Gray4 = 3,
};

// A non-owning view over generated icon data. The renderer decides how to
// read the bytes and how to map them to a particular display.
struct Icon {
    const uint8_t* data;
    uint16_t width;
    uint16_t height;
    // Bytes per row for MonoRowMajor, bytes per 8-pixel page for
    // MonoVertical. Grayscale formats are reserved for a later renderer.
    uint16_t stride;
    uint32_t byteCount;
    PixelFormat format;

    constexpr Icon(const uint8_t* data_, uint16_t width_, uint16_t height_, uint16_t stride_,
                   uint32_t byteCount_, PixelFormat format_)
        : data(data_), width(width_), height(height_), stride(stride_), byteCount(byteCount_),
          format(format_) {}
};

inline uint8_t readByte(const uint8_t* address) {
#if defined(__AVR__)
    return pgm_read_byte(address);
#else
    return *address;
#endif
}

} // namespace uicons
