// Golden-image test over a real generated icon.
//
// scripts/quality.sh builds tests/golden/uicons.json into a temporary directory
// and compiles this file with that directory on the include path, so the test
// exercises the full generator-to-renderer chain on checked-in masters.

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <uicons.h>
#include <uicons_generated.h>

namespace {

// 16x16 canvas in row-major order: 2 bytes per row.
const size_t kPbmCapacity = 1024;

void writeFramebufferPixel(void* context, int16_t x, int16_t y, uint32_t color) {
    (void)color;
    uint8_t* data = static_cast<uint8_t*>(context);
    data[static_cast<uint32_t>(y) * 2u + static_cast<uint32_t>(x) / 8u] |=
        static_cast<uint8_t>(0x80u >> (x % 8));
}

size_t toPbm(const uint8_t* data, char* output, size_t capacity) {
    size_t length = 0;
    length += static_cast<size_t>(snprintf(output + length, capacity - length, "P1\n16 16\n"));
    for (uint16_t y = 0; y < 16; ++y) {
        for (uint16_t x = 0; x < 16; ++x) {
            assert(length + 2 < capacity);
            const bool lit =
                (data[static_cast<uint32_t>(y) * 2u + x / 8u] & (0x80u >> (x % 8u))) != 0;
            output[length++] = lit ? '1' : '0';
            output[length++] = (x + 1u < 16u) ? ' ' : '\n';
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

} // namespace

int main() {
    uint8_t buffer[32] = {0};
    uicons::Canvas canvas(buffer, 16, 16, writeFramebufferPixel);

    const bool drawn = uicons::render(uicons::generated::fas_heart_16x16, canvas, 0, 0);
    assert(drawn);

    char actual[kPbmCapacity];
    const size_t actualLength = toPbm(buffer, actual, sizeof(actual));
    char expected[kPbmCapacity];
    const size_t expectedLength =
        readFile("tests/golden/fas-heart-16.pbm", expected, sizeof(expected));
    if (actualLength != expectedLength || memcmp(actual, expected, actualLength) != 0) {
        fprintf(stderr, "golden mismatch: tests/golden/fas-heart-16.pbm\n");
    }
    assert(actualLength == expectedLength);
    assert(memcmp(actual, expected, actualLength) == 0);

    printf("pack golden test passed\n");
    return 0;
}
