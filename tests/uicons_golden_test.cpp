// Host-side golden-image tests for the uIcons renderer.
//
// Each test renders a fixed scene into a caller-owned 1-bpp buffer, serializes
// the buffer to ASCII PBM (P1), and compares the result byte-for-byte against
// a checked-in file under tests/golden. The test must run from the repository
// root, which scripts/quality.sh guarantees. Only fixed-size buffers are used,
// keeping the test close to embedded constraints.

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <uicons.h>
#include <uicons/adapters/mono_framebuffer.h>
#include <uicons/adapters/mono_pages.h>

namespace {

// 4x3 image:
// #.#.
// .##.
// #..#
// cppcheck-suppress unknownMacro
const uint8_t rowMajorData[] UICONS_PROGMEM = {0xa0, 0x60, 0x90};

// The same image in vertical/page format: one byte per column, bit 0 first.
// cppcheck-suppress unknownMacro
const uint8_t verticalData[] UICONS_PROGMEM = {0x05, 0x02, 0x03, 0x04};

const uicons::Icon rowIcon(rowMajorData, 4, 3, 1, sizeof(rowMajorData),
                           uicons::PixelFormat::MonoRowMajor);
const uicons::Icon verticalIcon(verticalData, 4, 3, 4, sizeof(verticalData),
                                uicons::PixelFormat::MonoVertical);

bool framebufferPixel(const uint8_t* data, uint16_t stride, uint16_t x, uint16_t y) {
    return (data[static_cast<uint32_t>(y) * stride + x / 8u] &
            static_cast<uint8_t>(0x80u >> (x % 8u))) != 0;
}

bool pagePixel(const uint8_t* data, uint16_t stride, uint16_t x, uint16_t y) {
    return (data[static_cast<uint32_t>(y / 8u) * stride + x] &
            static_cast<uint8_t>(1u << (y % 8u))) != 0;
}

// The largest golden scene is 6x10 pixels: "P1\n6 10\n" plus two characters
// per pixel fits in 256 bytes with margin.
const size_t kPbmCapacity = 256;

size_t toPbm(bool (*pixel)(const uint8_t*, uint16_t, uint16_t, uint16_t), const uint8_t* data,
             uint16_t stride, uint16_t width, uint16_t height, char* output, size_t capacity) {
    size_t length = 0;
    length += static_cast<size_t>(
        snprintf(output + length, capacity - length, "P1\n%u %u\n", width, height));
    for (uint16_t y = 0; y < height; ++y) {
        for (uint16_t x = 0; x < width; ++x) {
            assert(length + 2 < capacity);
            output[length++] = pixel(data, stride, x, y) ? '1' : '0';
            output[length++] = (x + 1u < width) ? ' ' : '\n';
        }
    }
    output[length] = '\0';
    return length;
}

size_t readFile(const char* path, char* output, size_t capacity) {
    FILE* file = fopen(path, "rb");
    assert(file != nullptr);
    const size_t count = fread(output, 1, capacity - 1, file);
    const int readError = ferror(file);
    assert(readError == 0);
    fclose(file);
    output[count] = '\0';
    return count;
}

void checkGolden(const char* path, const char* actual, size_t actualLength) {
    char expected[kPbmCapacity];
    const size_t expectedLength = readFile(path, expected, sizeof(expected));
    if (actualLength != expectedLength || memcmp(actual, expected, actualLength) != 0) {
        fprintf(stderr, "golden mismatch: %s\n--- actual ---\n%s--- expected ---\n%s", path, actual,
                expected);
    }
    assert(actualLength == expectedLength);
    assert(memcmp(actual, expected, actualLength) == 0);
}

void testRowMajorGolden() {
    uint8_t buffer[5] = {0};
    uicons::adapters::MonoFramebuffer framebuffer(buffer, 6, 5, 1);

    assert(uicons::adapters::render(rowIcon, framebuffer, 1, 1));
    char actual[kPbmCapacity];
    const size_t length = toPbm(framebufferPixel, buffer, 1, 6, 5, actual, sizeof(actual));
    checkGolden("tests/golden/row-major.pbm", actual, length);
}

void testRowMajorClippedGolden() {
    uint8_t buffer[5] = {0};
    uicons::adapters::MonoFramebuffer framebuffer(buffer, 6, 5, 1);

    assert(uicons::adapters::render(rowIcon, framebuffer, -2, -1));
    char actual[kPbmCapacity];
    const size_t length = toPbm(framebufferPixel, buffer, 1, 6, 5, actual, sizeof(actual));
    checkGolden("tests/golden/row-major-clipped.pbm", actual, length);
}

void testVerticalPagesGolden() {
    uint8_t buffer[12] = {0};
    uicons::adapters::MonoPages pages(buffer, 6, 10, 6);

    assert(uicons::adapters::render(verticalIcon, pages, 1, 1));
    char actual[kPbmCapacity];
    const size_t length = toPbm(pagePixel, buffer, 6, 6, 10, actual, sizeof(actual));
    checkGolden("tests/golden/vertical-pages.pbm", actual, length);
}

void writeFramebufferPixel(void* context, int16_t x, int16_t y, uint32_t color) {
    (void)color;
    uint8_t* data = static_cast<uint8_t*>(context);
    data[static_cast<uint32_t>(y)] |= static_cast<uint8_t>(0x80u >> x);
}

void testRotated90Golden() {
    uint8_t buffer[4] = {0};
    uicons::Canvas canvas(buffer, 3, 4, writeFramebufferPixel);

    const bool drawn = uicons::renderRotated(rowIcon, canvas, 0, 0, uicons::Rotation::Deg90);
    assert(drawn);
    char actual[kPbmCapacity];
    const size_t length = toPbm(framebufferPixel, buffer, 1, 3, 4, actual, sizeof(actual));
    checkGolden("tests/golden/rotated-90.pbm", actual, length);
}

void testProgmemAccess() {
    // Icon data lives behind UICONS_PROGMEM; every byte must round-trip
    // through readByte, which is pgm_read_byte on AVR.
    assert(uicons::readByte(rowMajorData + 0) == 0xa0);
    assert(uicons::readByte(rowMajorData + 1) == 0x60);
    assert(uicons::readByte(rowMajorData + 2) == 0x90);
    assert(uicons::readByte(verticalData + 3) == 0x04);
}

} // namespace

int main() {
    testRowMajorGolden();
    testRowMajorClippedGolden();
    testVerticalPagesGolden();
    testRotated90Golden();
    testProgmemAccess();
    printf("golden tests passed\n");
    return 0;
}
