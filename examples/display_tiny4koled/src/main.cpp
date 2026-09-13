// Blits the generated fas/heart 16x16 icon straight from flash into an SSD1306
// window. The manifest uses mono-vertical, which matches the SSD1306 page
// layout, and bitmap() reads through pgm_read_byte, so no RAM buffer is needed.
#include <Arduino.h>
#include <Tiny4kOLED.h>

#include <uicons.h>

#include <uicons_generated.h>

void setup() {
    oled.begin();
    oled.clear();

    // 16x16 icon at pixel (56, 8): pages 1..2, 16 columns x 2 pages = 32 bytes.
    const uicons::Icon& heart = uicons::generated::fas_heart_16x16;
    oled.bitmap(56, 1, 56 + heart.width, 1 + heart.height / 8, heart.data);
    oled.on();
}

void loop() {
}
