#include <assert.h>

#include <fontawesome.h>
#include <uicons.h>

int main() {
    static_assert(UICONS_VERSION_MAJOR == 0, "unexpected uIcons major version");
    static_assert(static_cast<int>(uicons::PixelFormat::MonoVertical) == 1,
                  "MonoVertical format value changed");

    const uicons::Icon icon(nullptr, 0, 0, 0, 0, uicons::PixelFormat::Gray4);
    assert(icon.data == nullptr);
    assert(icon.format == uicons::PixelFormat::Gray4);
    return 0;
}
