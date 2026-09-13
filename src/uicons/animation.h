#pragma once

#include <stdint.h>

#include <uicons/renderer.h>

namespace uicons {

// Pre-rendered frame animation with a non-blocking player.
//
// The application owns time: it passes a millisecond timestamp (for example
// from millis()) to update() and draw(). Elapsed time is computed with
// unsigned subtraction, so the millisecond counter may wrap around. Nothing
// here calls delay(), allocates, throws, or owns the application scheduler.
struct AnimationFrame {
    const Icon* icon;
    uint32_t durationMs;

    constexpr AnimationFrame(const Icon* icon_, uint32_t durationMs_)
        : icon(icon_), durationMs(durationMs_) {}
};

struct Animation {
    const AnimationFrame* frames;
    // Number of frames in one loop. A value of 0 means loop forever.
    uint16_t frameCount;
    uint16_t loopCount;

    constexpr Animation(const AnimationFrame* frames_, uint16_t frameCount_, uint16_t loopCount_)
        : frames(frames_), frameCount(frameCount_), loopCount(loopCount_) {}
};

// Caller-owned playback state. Keep one Player per on-screen animation; the
// frame data itself is shared, read-only, and typically lives in flash.
struct Player {
    bool started;
    bool finished;
    uint16_t frameIndex;
    uint16_t loopsCompleted;
    uint32_t startTimeMs;

    constexpr Player()
        : started(false), finished(false), frameIndex(0), loopsCompleted(0), startTimeMs(0) {}
};

inline uint32_t totalDurationMs(const Animation& animation) {
    uint32_t total = 0;
    if (animation.frames == nullptr) {
        return 0;
    }
    for (uint16_t i = 0; i < animation.frameCount; ++i) {
        total += animation.frames[i].durationMs;
    }
    return total;
}

namespace detail {

inline uint16_t frameAt(const Animation& animation, uint32_t timeMs) {
    uint32_t accumulated = 0;
    for (uint16_t i = 0; i < animation.frameCount; ++i) {
        accumulated += animation.frames[i].durationMs;
        if (timeMs < accumulated) {
            return i;
        }
    }
    return static_cast<uint16_t>(animation.frameCount - 1u);
}

inline bool validAnimation(const Animation& animation) {
    return animation.frames != nullptr && animation.frameCount > 0 &&
           totalDurationMs(animation) > 0;
}

} // namespace detail

// Start playback from the first frame. Returns false when the animation holds
// no playable frames; the player is left stopped in that case.
inline bool start(Player& player, const Animation& animation, uint32_t nowMs) {
    if (!detail::validAnimation(animation)) {
        return false;
    }
    player.started = true;
    player.finished = false;
    player.frameIndex = 0;
    player.loopsCompleted = 0;
    player.startTimeMs = nowMs;
    return true;
}

inline void stop(Player& player) {
    player.started = false;
    player.finished = false;
    player.frameIndex = 0;
    player.loopsCompleted = 0;
}

// Advance playback to nowMs. Returns true only when the visible frame changed,
// so the application can skip redraws. Never blocks and never reads a clock.
inline bool update(Player& player, const Animation& animation, uint32_t nowMs) {
    if (!player.started || player.finished || !detail::validAnimation(animation)) {
        return false;
    }

    const uint32_t total = totalDurationMs(animation);
    const uint32_t elapsed = nowMs - player.startTimeMs; // Wraps safely.
    uint16_t index = 0;

    if (animation.loopCount == 0) {
        index = detail::frameAt(animation, elapsed % total);
    } else {
        const uint32_t completed = elapsed / total;
        if (completed >= animation.loopCount) {
            const bool changed = !player.finished || player.frameIndex != animation.frameCount - 1u;
            player.frameIndex = static_cast<uint16_t>(animation.frameCount - 1u);
            player.loopsCompleted = animation.loopCount;
            player.finished = true;
            return changed;
        }
        player.loopsCompleted = static_cast<uint16_t>(completed);
        index = detail::frameAt(animation, elapsed % total);
    }

    const bool changed = index != player.frameIndex;
    player.frameIndex = index;
    return changed;
}

inline bool isFinished(const Player& player) {
    return player.finished;
}

// Current frame icon, or nullptr before the first start().
inline const Icon* currentIcon(const Player& player, const Animation& animation) {
    if (!player.started || !detail::validAnimation(animation)) {
        return nullptr;
    }
    return animation.frames[player.frameIndex].icon;
}

// Advance to nowMs and draw the current frame. Returns the render result, or
// false before the first start().
inline bool draw(Player& player, const Animation& animation, const Canvas& canvas, int16_t x,
                 int16_t y, uint32_t nowMs, uint32_t color = 1) {
    update(player, animation, nowMs);
    const Icon* icon = currentIcon(player, animation);
    if (icon == nullptr) {
        return false;
    }
    return render(*icon, canvas, x, y, color);
}

} // namespace uicons
