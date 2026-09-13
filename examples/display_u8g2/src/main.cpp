// Draws the generated fas/heart 16x16 icon through U8g2. Note drawXBM is NOT
// used: it expects LSB-first XBM rows while uIcons rows are MSB-first.
#include <Arduino.h>
#include <U8g2lib.h>

#include <uicons.h>

#include <uicons_generated.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0);

void setU8g2Pixel(void* context, int16_t x, int16_t y, uint32_t color) {
    if (color != 0) {
        static_cast<U8G2*>(context)->drawPixel(static_cast<u8g2_uint_t>(x),
                                               static_cast<u8g2_uint_t>(y));
    }
}

void setup() {
    u8g2.begin();
}

void loop() {
    u8g2.clearBuffer();
    const uicons::Canvas canvas(&u8g2, 128, 64, setU8g2Pixel);
    uicons::render(uicons::generated::fas_heart_16x16, canvas, 56, 24);
    u8g2.sendBuffer();
    delay(1000);
}
