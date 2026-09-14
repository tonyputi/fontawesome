#!/usr/bin/env bash
# uIcons quality gate: identical locally and in CI.
#
# Run everything (the default) or iterate on one phase:
#   ./scripts/quality.sh [all|format|host|python|drift|examples|tidy|cppcheck|package]...
#
# Phase order for a full run: format, host, python, drift, examples, tidy,
# cppcheck, package. The versions preamble always runs first so a failure log
# records the exact toolchain. Steps that are chatty on success (generator
# builds, PlatformIO builds, packaging) log to files and only print their
# output when they fail, so failure context is never lost.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/uicons-quality.XXXXXX")"
LOGS_DIR="$BUILD_DIR/logs"
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

HOST_TESTS=(
    tests/uicons_renderer_test.cpp
    tests/uicons_api_test.cpp
    tests/uicons_golden_test.cpp
    tests/uicons_animation_test.cpp
)

CXX_BIN="${CXX:-c++}"
CXX_FLAGS=(-std=c++11 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror)

need() {
    command -v "$1" >/dev/null || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

# run_quiet <step> <command...>: log step output to a file; print it only on
# failure so quiet successes stay quiet and failures keep full context.
run_quiet() {
    local step="$1"
    shift
    local log
    log="$LOGS_DIR/$step.log"
    mkdir -p "$(dirname "$log")"
    printf '%s\n' "== $step =="
    if "$@" >"$log" 2>&1; then
        return 0
    fi
    local status
    status=$?
    printf 'error: step %s failed (exit %d), full output:\n' "$step" "$status" >&2
    cat "$log" >&2
    return "$status"
}

version_line() {
    if command -v "$1" >/dev/null; then
        printf '%s: %s\n' "$1" "$("$1" --version 2>&1 | head -n 1)"
    else
        printf '%s: MISSING\n' "$1"
    fi
}

phase_versions() {
    printf '%s\n' '== versions =='
    printf 'python3: %s\n' "$(python3 --version 2>&1)"
    version_line "$CXX_BIN"
    version_line clang-format
    version_line clang-tidy
    version_line cppcheck
    version_line pio
    version_line ruff
}

phase_format() {
    need clang-format
    printf '%s\n' '== clang-format =='
    clang-format --dry-run --Werror "${HAND_WRITTEN_CPP[@]}"
}

gen_golden_header() {
    ./scripts/uicons build --manifest tests/golden/uicons.json --output-dir "$BUILD_DIR/gen-golden" >/dev/null
}

phase_host() {
    need "$CXX_BIN"
    printf '%s\n' '== host tests =='
    for test in "${HOST_TESTS[@]}"; do
        name="$(basename "$test" .cpp)"
        run_quiet "host-$name" "$CXX_BIN" "${CXX_FLAGS[@]}" -Isrc "$test" -o "$BUILD_DIR/$name"
        "$BUILD_DIR/$name"
    done
    gen_golden_header
    run_quiet host-uicons_pack_golden_test "$CXX_BIN" "${CXX_FLAGS[@]}" \
        -Isrc -I"$BUILD_DIR/gen-golden" tests/uicons_pack_golden_test.cpp \
        -o "$BUILD_DIR/uicons_pack_golden_test"
    "$BUILD_DIR/uicons_pack_golden_test"
}

phase_python() {
    command -v ruff >/dev/null || {
        echo "error: ruff not found (dev-only lint): pip install 'ruff==0.16.7'" >&2
        exit 1
    }
    printf '%s\n' '== Python lint (dev-only, stdlib runtime untouched) =='
    ruff check tools/ tests/
    printf '%s\n' '== Python generator tests =='
    python3 -m unittest discover --start-directory tests --pattern 'test_*.py'
}

phase_drift() {
    printf '%s\n' '== generation drift =='
    for manifest in examples/uicons.json examples/lucide.json examples/heroicons.json examples/animation.json; do
        name="$(basename "$manifest" .json)"
        run_quiet "drift-$name-a" ./scripts/uicons build --manifest "$manifest" --output-dir "$BUILD_DIR/gen-a-$name"
        run_quiet "drift-$name-b" ./scripts/uicons build --manifest "$manifest" --output-dir "$BUILD_DIR/gen-b-$name"
        cmp "$BUILD_DIR/gen-a-$name/uicons_generated.h" "$BUILD_DIR/gen-b-$name/uicons_generated.h"
        run_quiet "report-$name" ./scripts/uicons report --manifest "$manifest"
    done

    printf '%s\n' '== example headers drift =='
    for example in examples/basic examples/display_u8g2 examples/display_adafruit examples/display_tiny4koled examples/target_esp32; do
        run_quiet "drift-$example" ./scripts/uicons build --manifest "$example/uicons.json" --output-dir "$BUILD_DIR/gen-example"
        if ! cmp "$BUILD_DIR/gen-example/uicons_generated.h" "$example/include/uicons_generated.h"; then
            printf 'drift detected: %s\n' "$example" >&2
            exit 1
        fi
    done
}

phase_examples() {
    need pio
    run_quiet examples make -C "$ROOT_DIR" examples
}

phase_tidy() {
    need clang-tidy
    need "$CXX_BIN"
    printf '%s\n' '== clang-tidy =='
    gen_golden_header
    clang-tidy tests/uicons_renderer_test.cpp tests/uicons_api_test.cpp tests/uicons_golden_test.cpp tests/uicons_animation_test.cpp tests/uicons_pack_golden_test.cpp --quiet -- -I"$BUILD_DIR/gen-golden" \
        -std=c++11 -Wall -Wextra -Wpedantic -Isrc
}

phase_cppcheck() {
    need cppcheck
    printf '%s\n' '== cppcheck =='
    cppcheck \
        --std=c++11 \
        --language=c++ \
        --enable=warning,performance,portability,style \
        --error-exitcode=1 \
        --inline-suppr \
        --suppressions-list=.cppcheck-suppressions \
        -Isrc \
        "${HAND_WRITTEN_CPP[@]}"
}

phase_package() {
    need pio
    run_quiet package pio pkg pack --output "$BUILD_DIR/uicons.tar.gz" .
    printf '%s\n' '== PlatformIO package =='
    tar -tzf "$BUILD_DIR/uicons.tar.gz" | sort > "$BUILD_DIR/package-contents.txt"
    if grep -E '(^|/)(assets|scripts|tools|tests|build)/' "$BUILD_DIR/package-contents.txt"; then
        printf '%s\n' 'error: package leaks development files' >&2
        exit 1
    fi
    # Boundary from the README: runtime + frozen legacy must ship, nothing else.
    for required in src/uicons.h src/uicons/icon.h src/fontawesome.h library.json; do
        if ! grep -qxF "$required" "$BUILD_DIR/package-contents.txt"; then
            printf 'error: package is missing required %s\n' "$required" >&2
            exit 1
        fi
    done
    if ! grep -q '^src/vertical/' "$BUILD_DIR/package-contents.txt"; then
        printf '%s\n' 'error: package is missing the frozen src/vertical catalog' >&2
        exit 1
    fi
}

ALL_PHASES=(format host python drift examples tidy cppcheck package)

USAGE_PHASES="$(IFS='|'; echo "${ALL_PHASES[*]}")"

usage() {
    echo "usage: quality.sh [all|versions|$USAGE_PHASES]..." >&2
    exit 1
}

SELECTED=()
if [ $# -eq 0 ]; then
    SELECTED=(all)
else
    SELECTED=("$@")
fi

EXPANDED=()
for phase in "${SELECTED[@]}"; do
    case "$phase" in
        all) EXPANDED+=("${ALL_PHASES[@]}") ;;
        versions) ;;
        format | host | python | drift | examples | tidy | cppcheck | package) EXPANDED+=("$phase") ;;
        *) usage ;;
    esac
done

phase_versions
for phase in "${EXPANDED[@]}"; do
    "phase_$phase"
done
printf 'quality checks passed\n'
