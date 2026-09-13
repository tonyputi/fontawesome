#include <algorithm>
#include <assert.h>
#include <iterator>
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

const uicons::Icon rowIcon(rowMajor, 4, 3, 1, sizeof(rowMajor), uicons::PixelFormat::MonoRowMajor);
const uicons::Icon verticalIcon(vertical, 4, 3, 4, sizeof(vertical),
                                uicons::PixelFormat::MonoVertical);

bool framebufferPixel(const uint8_t* data, uint16_t stride, uint16_t x, uint16_t y) {
    return (data[static_cast<uint32_t>(y) * stride + x / 8u] &
            static_cast<uint8_t>(0x80u >> (x % 8u))) != 0;
}

bool pagePixel(const uint8_t* data, uint16_t stride, uint16_t x, uint16_t y) {
    return (data[static_cast<uint32_t>(y / 8u) * stride + x] &
            static_cast<uint8_t>(1u << (y % 8u))) != 0;
}

void assertShape(bool (*pixel)(const uint8_t*, uint16_t, uint16_t, uint16_t), const uint8_t* data,
                 uint16_t stride) {
    const uint16_t expected[][2] = {
        {1, 1}, {3, 1}, {2, 2}, {3, 2}, {1, 3}, {4, 3},
    };

    for (uint16_t y = 0; y < 5; ++y) {
        for (uint16_t x = 0; x < 6; ++x) {
            const bool expectedPixel = std::any_of(
                std::begin(expected), std::end(expected),
                [x, y](const uint16_t* point) { return point[0] == x && point[1] == y; });
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

void testRotationMatchesUnrotatedRender() {
    uint8_t plain[5] = {0};
    uint8_t rotated[5] = {0};
    uicons::adapters::MonoFramebuffer plainFramebuffer(plain, 6, 5, 1);
    uicons::adapters::MonoFramebuffer rotatedFramebuffer(rotated, 6, 5, 1);

    assert(uicons::adapters::render(rowIcon, plainFramebuffer, 1, 1));
    uicons::Canvas canvas(&rotatedFramebuffer, rotatedFramebuffer.width, rotatedFramebuffer.height,
                          uicons::adapters::detail::setFramebufferPixel);
    assert(uicons::renderRotated(rowIcon, canvas, 1, 1, uicons::Rotation::Deg0));
    assert(std::equal(std::begin(plain), std::end(plain), std::begin(rotated)));
}

void testRotationTransforms() {
    // 4x3 source rotated 180 degrees maps (x, y) to (3 - x, 2 - y).
    uint8_t buffer[3] = {0};
    uicons::Canvas canvas(&buffer, 4, 3, [](void* context, int16_t x, int16_t y, uint32_t color) {
        (void)color;
        uint8_t* data = static_cast<uint8_t*>(context);
        data[static_cast<uint32_t>(y)] |= static_cast<uint8_t>(0x80u >> x);
    });
    assert(uicons::renderRotated(rowIcon, canvas, 0, 0, uicons::Rotation::Deg180));
    // (0,0)->(3,2), (2,0)->(1,2), (1,1)->(2,1), (2,1)->(1,1), (0,2)->(3,0), (3,2)->(0,0).
    const uint8_t expected[] = {0x90, 0x60, 0x50};
    assert(std::equal(std::begin(expected), std::end(expected), buffer));

    uint8_t wide[4] = {0};
    uicons::Canvas wideCanvas(&wide, 3, 4, [](void* context, int16_t x, int16_t y, uint32_t color) {
        (void)color;
        uint8_t* data = static_cast<uint8_t*>(context);
        data[static_cast<uint32_t>(y)] |= static_cast<uint8_t>(0x80u >> x);
    });
    assert(uicons::renderRotated(rowIcon, wideCanvas, 0, 0, uicons::Rotation::Deg270));
    // (0,0)->(0,3), (2,0)->(0,1), (1,1)->(1,2), (2,1)->(1,1), (0,2)->(2,3), (3,2)->(2,0).
    const uint8_t expected270[] = {0x20, 0xc0, 0x40, 0xa0};
    assert(std::equal(std::begin(expected270), std::end(expected270), wide));
}

void testInvalidRotation() {
    uint8_t buffer[5] = {0};
    uicons::Canvas canvas(&buffer, 6, 5, [](void* context, int16_t x, int16_t y, uint32_t color) {
        (void)context;
        (void)x;
        (void)y;
        (void)color;
    });
    assert(!uicons::renderRotated(rowIcon, canvas, 0, 0, static_cast<uicons::Rotation>(9)));
}

void testInvalidFormats() {
    uint8_t buffer[1] = {0};
    uicons::adapters::MonoFramebuffer framebuffer(buffer, 8, 1, 1);
    const uicons::Icon grayscale(nullptr, 8, 1, 1, 1, uicons::PixelFormat::Gray2);

    assert(!uicons::adapters::render(grayscale, framebuffer, 0, 0));
}

} // namespace

int main() {
    testRowMajorFramebuffer();
    testVerticalPages();
    testRotationMatchesUnrotatedRender();
    testRotationTransforms();
    testInvalidRotation();
    testInvalidFormats();
    return 0;
}
