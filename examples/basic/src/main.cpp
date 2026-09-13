// Renders the generated fas/heart 16x16 icon into a page buffer and checks the
// pixel count against the checked-in golden (tests/golden/fas-heart-16.pbm).
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include <uicons.h>
#include <uicons/adapters/mono_pages.h>

#include <uicons_generated.h>

int main() {
    uint8_t buffer[32] = {0};
    uicons::adapters::MonoPages pages(buffer, 16, 16, 16);

    const bool drawn = uicons::adapters::render(uicons::generated::fas_heart_16x16, pages, 0, 0);
    assert(drawn);

    unsigned lit = 0;
    for (size_t i = 0; i < sizeof(buffer); ++i) {
        uint8_t byte = buffer[i];
        while (byte != 0) {
            lit += byte & 1u;
            byte >>= 1;
        }
    }
    printf("lit pixels: %u\n", lit);
    assert(lit == 158);

    printf("basic example OK\n");
    return 0;
}
