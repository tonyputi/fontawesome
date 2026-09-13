#pragma once

#include <stdint.h>

#if defined(__AVR__) && !defined(PROGMEM)
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
    uint16_t stride;
    uint32_t byteCount;
    PixelFormat format;

    constexpr Icon(const uint8_t* data_,
                   uint16_t width_,
                   uint16_t height_,
                   uint16_t stride_,
                   uint32_t byteCount_,
                   PixelFormat format_)
        : data(data_),
          width(width_),
          height(height_),
          stride(stride_),
          byteCount(byteCount_),
          format(format_) {}
};

}  // namespace uicons
