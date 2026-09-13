#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/uicons-quality.XXXXXX")"
trap 'rm -rf "$BUILD_DIR"' EXIT

cd "$ROOT_DIR"

HAND_WRITTEN_CPP=(
    src/uicons.h
    src/uicons/icon.h
    src/uicons/renderer.h
    src/uicons/adapters/mono_framebuffer.h
    src/uicons/adapters/mono_pages.h
    tests/uicons_renderer_test.cpp
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

printf '%s\n' '== clang-tidy =='
clang-tidy tests/uicons_renderer_test.cpp --quiet -- \
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
    src/uicons/icon.h \
    src/uicons/renderer.h \
    src/uicons/adapters/mono_framebuffer.h \
    src/uicons/adapters/mono_pages.h \
    tests/uicons_renderer_test.cpp

printf '%s\n' '== PlatformIO package =='
pio pkg pack --output "$BUILD_DIR/uicons.tar.gz" . >/dev/null
printf 'quality checks passed\n'
