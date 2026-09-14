// ESP32 compile smoke: renders the generated fas/heart 16x16 icon into a page
// buffer. Runtime asserts match examples/basic; on-device this is a build
// check that the core headers survive the xtensa toolchain with -Werror.
#include <Arduino.h>
#include <assert.h>

#include <uicons.h>
#include <uicons/adapters/mono_pages.h>

#include <uicons_generated.h>

void setup() {
    static uint8_t buffer[32] = {0};
    uicons::adapters::MonoPages pages(buffer, 16, 16, 16);

    const bool drawn = uicons::adapters::render(uicons::generated::fas_heart_16x16, pages, 0, 0);
    assert(drawn);

    unsigned lit = 0;
    for (size_t i = 0; i < sizeof(buffer); ++i) {
        uint8_t byte = buffer[i];
        while (byte != 0) {
            lit += static_cast<unsigned>(byte & 1u);
            byte >>= 1;
        }
    }
    assert(lit == 158);
}

void loop() {}
