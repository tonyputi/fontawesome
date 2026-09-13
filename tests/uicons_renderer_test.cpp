#include <assert.h>
#include <stdint.h>

#include <uicons/adapters/mono_framebuffer.h>
#include <uicons/adapters/mono_pages.h>

namespace {

// 4x3 image:
// #.#.
// .##.
// #..#
const uint8_t rowMajor[] = {0xa0, 0x60, 0x90};

// The same image in vertical/page format: one byte per column, bit 0 first.
const uint8_t vertical[] = {0x05, 0x02, 0x03, 0x04};

const uicons::Icon rowIcon(rowMajor,
                           4,
                           3,
                           1,
                           sizeof(rowMajor),
                           uicons::PixelFormat::MonoRowMajor);
const uicons::Icon verticalIcon(vertical,
                                4,
                                3,
                                4,
                                sizeof(vertical),
                                uicons::PixelFormat::MonoVertical);

bool framebufferPixel(const uint8_t* data,
                      uint16_t stride,
                      uint16_t x,
                      uint16_t y) {
    return (data[static_cast<uint32_t>(y) * stride + x / 8u] &
            static_cast<uint8_t>(0x80u >> (x % 8u))) != 0;
}

bool pagePixel(const uint8_t* data,
               uint16_t stride,
               uint16_t x,
               uint16_t y) {
    return (data[static_cast<uint32_t>(y / 8u) * stride + x] &
            static_cast<uint8_t>(1u << (y % 8u))) != 0;
}

void assertShape(bool (*pixel)(const uint8_t*, uint16_t, uint16_t, uint16_t),
                 const uint8_t* data,
                 uint16_t stride) {
    const uint16_t expected[][2] = {
        {1, 1}, {3, 1}, {2, 2}, {3, 2}, {1, 3}, {4, 3},
    };

    for (uint16_t y = 0; y < 5; ++y) {
        for (uint16_t x = 0; x < 6; ++x) {
            bool expectedPixel = false;
            for (const auto& point : expected) {
                if (point[0] == x && point[1] == y) {
                    expectedPixel = true;
                    break;
                }
            }
            assert(pixel(data, stride, x, y) == expectedPixel);
        }
    }
}

void testRowMajorFramebuffer() {
    uint8_t buffer[5] = {0};
    uicons::adapters::MonoFramebuffer framebuffer(buffer, 6, 5, 1);

    assert(uicons::adapters::render(rowIcon, framebuffer, 1, 1));
    assertShape(framebufferPixel, buffer, 1);

    // Rendering partially outside the canvas is clipped by the renderer.
    assert(uicons::adapters::render(rowIcon, framebuffer, -2, -1));
}

void testVerticalPages() {
    uint8_t buffer[12] = {0};
    uicons::adapters::MonoPages pages(buffer, 6, 10, 6);

    assert(uicons::adapters::render(verticalIcon, pages, 1, 1));
    assertShape(pagePixel, buffer, 6);
}

void testInvalidFormats() {
    uint8_t buffer[1] = {0};
    uicons::adapters::MonoFramebuffer framebuffer(buffer, 8, 1, 1);
    const uicons::Icon grayscale(nullptr,
                                 8,
                                 1,
                                 1,
                                 1,
                                 uicons::PixelFormat::Gray2);

    assert(!uicons::adapters::render(grayscale, framebuffer, 0, 0));
}

}  // namespace

int main() {
    testRowMajorFramebuffer();
    testVerticalPages();
    testInvalidFormats();
    return 0;
}
