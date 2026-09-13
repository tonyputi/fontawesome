#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/uicons-quality.XXXXXX")"
trap 'rm -rf "$BUILD_DIR"' EXIT

cd "$ROOT_DIR"

HAND_WRITTEN_CPP=(
    src/uicons.h
    src/uicons/animation.h
    src/uicons/icon.h
    src/uicons/renderer.h
    src/uicons/adapters/mono_framebuffer.h
    src/uicons/adapters/mono_pages.h
    tests/uicons_renderer_test.cpp
    tests/uicons_api_test.cpp
    tests/uicons_golden_test.cpp
    tests/uicons_animation_test.cpp
    tests/uicons_pack_golden_test.cpp
)

for command in clang-format clang-tidy cppcheck pio; do
    command -v "$command" >/dev/null || {
        echo "error: required command not found: $command" >&2
        exit 1
    }
done

printf '%s\n' '== clang-format =='
clang-format --dry-run --Werror "${HAND_WRITTEN_CPP[@]}"

printf '%s\n' '== host tests =='
"${CXX:-c++}" \
    -std=c++11 \
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
    -Isrc tests/uicons_renderer_test.cpp \
    -o "$BUILD_DIR/uicons_renderer_test"
"$BUILD_DIR/uicons_renderer_test"
"${CXX:-c++}" \
    -std=c++11 \
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
    -Isrc tests/uicons_api_test.cpp \
    -o "$BUILD_DIR/uicons_api_test"
"$BUILD_DIR/uicons_api_test"
"${CXX:-c++}" \
    -std=c++11 \
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
    -Isrc tests/uicons_golden_test.cpp \
    -o "$BUILD_DIR/uicons_golden_test"
"$BUILD_DIR/uicons_golden_test"
"${CXX:-c++}" \
    -std=c++11 \
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
    -Isrc tests/uicons_animation_test.cpp \
    -o "$BUILD_DIR/uicons_animation_test"
"$BUILD_DIR/uicons_animation_test"
./scripts/uicons build --manifest tests/golden/uicons.json --output-dir "$BUILD_DIR/gen-golden" >/dev/null
"${CXX:-c++}" \
    -std=c++11 \
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
    -Isrc -I"$BUILD_DIR/gen-golden" tests/uicons_pack_golden_test.cpp \
    -o "$BUILD_DIR/uicons_pack_golden_test"
"$BUILD_DIR/uicons_pack_golden_test"

printf '%s\n' '== Python generator tests =='
python3 -m unittest discover --start-directory tests --pattern 'test_*.py'

printf '%s\n' '== generation drift =='
for manifest in examples/uicons.json examples/lucide.json examples/animation.json; do
    name="$(basename "$manifest" .json)"
    ./scripts/uicons build --manifest "$manifest" --output-dir "$BUILD_DIR/gen-a-$name" >/dev/null
    ./scripts/uicons build --manifest "$manifest" --output-dir "$BUILD_DIR/gen-b-$name" >/dev/null
    cmp "$BUILD_DIR/gen-a-$name/uicons_generated.h" "$BUILD_DIR/gen-b-$name/uicons_generated.h"
    ./scripts/uicons report --manifest "$manifest" >/dev/null
done

printf '%s\n' '== clang-tidy =='
clang-tidy tests/uicons_renderer_test.cpp tests/uicons_api_test.cpp tests/uicons_golden_test.cpp tests/uicons_animation_test.cpp tests/uicons_pack_golden_test.cpp --quiet -- -I"$BUILD_DIR/gen-golden" \
    -std=c++11 -Wall -Wextra -Wpedantic -Isrc

printf '%s\n' '== cppcheck =='
cppcheck \
    --std=c++11 \
    --language=c++ \
    --enable=warning,performance,portability,style \
    --error-exitcode=1 \
    --inline-suppr \
    --suppressions-list=.cppcheck-suppressions \
    -Isrc \
    src/uicons.h \
    src/uicons/animation.h \
    src/uicons/icon.h \
    src/uicons/renderer.h \
    src/uicons/adapters/mono_framebuffer.h \
    src/uicons/adapters/mono_pages.h \
    tests/uicons_renderer_test.cpp \
    tests/uicons_api_test.cpp \
    tests/uicons_golden_test.cpp \
    tests/uicons_animation_test.cpp \
    tests/uicons_pack_golden_test.cpp

printf '%s\n' '== PlatformIO package =='
pio pkg pack --output "$BUILD_DIR/uicons.tar.gz" . >/dev/null
printf 'quality checks passed\n'
