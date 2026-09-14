// On-target PROGMEM proof for real and simulated (SimAVR) ATmega328P.
//
// Prints "SIMAVR-TEST PASS" over a polled UART at 9600 baud. Polling is
// deliberate: Arduino Serial is interrupt-driven, and the SimAVR build
// shipped by PlatformIO never delivers the UART data-register interrupt, so
// interrupt-driven output stays silent under simulation. Polled bytes work on
// every host and on real hardware alike. Host tests pin exact pixels; this
// proves the same bytes come out of real flash reads (pgm_read_byte), which
// host builds cannot exercise.
#include <Arduino.h>
#include <avr/io.h>
#include <stdlib.h>

#include <uicons.h>
#include <uicons/adapters/mono_pages.h>

#include <uicons_generated.h>

static uint8_t s_buffer[32];

static void putcPoll(char c) {
    while ((UCSR0A & (1 << UDRE0)) == 0) {
    }
    UDR0 = static_cast<uint8_t>(c);
}

static void printPoll(const char* text) {
    while (*text != '\0') {
        putcPoll(*text);
        ++text;
    }
}

void setup() {
    // 9600 baud at 16 MHz, polled: no interrupts involved.
    UBRR0H = 0;
    UBRR0L = 103;
    UCSR0B = (1 << TXEN0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);

    uicons::adapters::MonoPages pages(s_buffer, 16, 16, 16);
    const bool drawn =
        uicons::adapters::render(uicons::generated::fas_heart_16x16, pages, 0, 0);

    unsigned lit = 0;
    for (size_t i = 0; i < sizeof(s_buffer); ++i) {
        uint8_t byte = s_buffer[i];
        while (byte != 0) {
            lit += static_cast<unsigned>(byte & 1u);
            byte >>= 1;
        }
    }
    char count[8] = {0};
    // Dump the framebuffer as ASCII art so a human (or a serial monitor)
    // can SEE the icon: '#' is a lit pixel, '.' is background. MonoPages
    // stores page-major bytes, so row y, column x lives in bit (y % 8) of
    // byte (y / 8) * 16 + x (see setPagePixel in mono_pages.h).
    printPoll("SIMAVR-TEST art:\n");
    for (uint8_t y = 0; y < 16; ++y) {
        for (uint8_t x = 0; x < 16; ++x) {
            const uint8_t byte =
                s_buffer[static_cast<size_t>(y) / 8u * 16u + x];
            putcPoll(((byte >> (y % 8u)) & 1u) != 0 ? '#' : '.');
        }
        putcPoll('\n');
    }
    printPoll("SIMAVR-TEST drawn=");
    putcPoll(drawn ? '1' : '0');
    printPoll(" lit=");
    printPoll(utoa(lit, count, 10));
    // Golden pin from tests/golden/fas-heart-16.pbm (158 lit pixels).
    printPoll((drawn && lit == 158) ? "\nSIMAVR-TEST PASS\n" : "\nSIMAVR-TEST FAIL\n");
}

void loop() {}
