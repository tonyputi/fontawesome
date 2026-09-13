// Host-side tests for non-blocking pre-rendered frame animations.
//
// Time is fully simulated: every test drives the player with explicit
// millisecond timestamps, including a 32-bit counter wrap-around.

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include <uicons.h>

namespace {

// Frame 0: 6 lit pixels. Frame 1: 12 lit pixels.
const uint8_t frame0Data[] = {0xa0, 0x60, 0x90};
const uint8_t frame1Data[] = {0xf0, 0xf0, 0xf0};

const uicons::Icon frame0Icon(frame0Data, 4, 3, 1, sizeof(frame0Data),
                              uicons::PixelFormat::MonoRowMajor);
const uicons::Icon frame1Icon(frame1Data, 4, 3, 1, sizeof(frame1Data),
                              uicons::PixelFormat::MonoRowMajor);

const uicons::AnimationFrame loopFrames[] = {
    uicons::AnimationFrame(&frame0Icon, 100),
    uicons::AnimationFrame(&frame1Icon, 200),
};
const uicons::Animation loopAnimation(loopFrames, 2, 0);

const uicons::AnimationFrame onceFrames[] = {
    uicons::AnimationFrame(&frame0Icon, 100),
    uicons::AnimationFrame(&frame1Icon, 200),
};
const uicons::Animation onceAnimation(onceFrames, 2, 1);

const uicons::Animation emptyAnimation(nullptr, 0, 0);

const uicons::AnimationFrame zeroFrames[] = {
    uicons::AnimationFrame(&frame0Icon, 0),
    uicons::AnimationFrame(&frame1Icon, 0),
};
const uicons::Animation zeroAnimation(zeroFrames, 2, 0);

void countPixel(void* context, int16_t x, int16_t y, uint32_t color) {
    (void)x;
    (void)y;
    (void)color;
    ++(*static_cast<unsigned*>(context));
}

void testInfiniteLoopSequence() {
    uicons::Player player;
    const bool started = uicons::start(player, loopAnimation, 1000);
    assert(started);
    assert(player.frameIndex == 0);

    bool changed = uicons::update(player, loopAnimation, 1000);
    assert(!changed);
    changed = uicons::update(player, loopAnimation, 1099);
    assert(!changed);
    changed = uicons::update(player, loopAnimation, 1100);
    assert(changed);
    assert(player.frameIndex == 1);
    changed = uicons::update(player, loopAnimation, 1299);
    assert(!changed);
    // Total duration is 300ms: the loop wraps back to frame 0.
    changed = uicons::update(player, loopAnimation, 1300);
    assert(changed);
    assert(player.frameIndex == 0);
    changed = uicons::update(player, loopAnimation, 1400);
    assert(changed);
    assert(player.frameIndex == 1);
    assert(!uicons::isFinished(player));
}

void testFiniteLoopFinishesOnLastFrame() {
    uicons::Player player;
    const bool started = uicons::start(player, onceAnimation, 0);
    assert(started);

    bool changed = uicons::update(player, onceAnimation, 99);
    assert(!changed);
    changed = uicons::update(player, onceAnimation, 100);
    assert(changed);
    assert(player.frameIndex == 1);
    assert(player.loopsCompleted == 0);
    changed = uicons::update(player, onceAnimation, 300);
    assert(changed);
    assert(player.frameIndex == 1);
    assert(player.loopsCompleted == 1);
    assert(uicons::isFinished(player));
    // A finished player reports no further changes.
    changed = uicons::update(player, onceAnimation, 10000);
    assert(!changed);
    assert(uicons::currentIcon(player, onceAnimation) == &frame1Icon);
}

void testCounterWrapAround() {
    uicons::Player player;
    const bool started = uicons::start(player, loopAnimation, 0xffffff00u);
    assert(started);

    // Elapsed 0x150 wraps the 32-bit counter; 336 % 300 == 36 -> frame 0.
    bool changed = uicons::update(player, loopAnimation, 0x00000050u);
    assert(!changed);
    assert(player.frameIndex == 0);
    // Elapsed 0x1e0 == 480; 480 % 300 == 180 -> frame 1.
    changed = uicons::update(player, loopAnimation, 0x000000e0u);
    assert(changed);
    assert(player.frameIndex == 1);
}

void testDrawRendersCurrentFrame() {
    unsigned lit = 0;
    uicons::Canvas canvas(&lit, 4, 3, countPixel);
    uicons::Player player;

    bool drawn = uicons::draw(player, loopAnimation, canvas, 0, 0, 0);
    assert(!drawn);

    const bool started = uicons::start(player, loopAnimation, 0);
    assert(started);
    drawn = uicons::draw(player, loopAnimation, canvas, 0, 0, 0);
    assert(drawn);
    assert(lit == 6);

    drawn = uicons::draw(player, loopAnimation, canvas, 0, 0, 150);
    assert(drawn);
    assert(lit == 6 + 12);
}

void testInvalidAnimationsDoNotStart() {
    uicons::Player player;
    bool started = uicons::start(player, emptyAnimation, 0);
    assert(!started);
    assert(!player.started);
    started = uicons::start(player, zeroAnimation, 0);
    assert(!started);
    assert(!player.started);
    assert(uicons::currentIcon(player, loopAnimation) == nullptr);
}

void testStopResets() {
    uicons::Player player;
    const bool started = uicons::start(player, loopAnimation, 0);
    assert(started);
    const bool changed = uicons::update(player, loopAnimation, 150);
    assert(changed);
    uicons::stop(player);
    assert(!player.started);
    assert(player.frameIndex == 0);
    const bool idle = uicons::update(player, loopAnimation, 10000);
    assert(!idle);
}

} // namespace

int main() {
    testInfiniteLoopSequence();
    testFiniteLoopFinishesOnLastFrame();
    testCounterWrapAround();
    testDrawRendersCurrentFrame();
    testInvalidAnimationsDoNotStart();
    testStopResets();
    printf("animation tests passed\n");
    return 0;
}
