#pragma once

// Legacy Font Awesome umbrella header. New code should include <uicons.h>.
#include <uicons.h>

// Generated legacy headers use PROGMEM directly. Keep the compatibility
// fallback local so native tests do not need Arduino headers and the macro is
// not exposed to users of the new API.
#ifndef PROGMEM
#define PROGMEM
#define UICONS_LEGACY_PROGMEM_FALLBACK
#endif

#include <vertical/fab_64x64.h>
#include <vertical/fab_32x32.h>
#include <vertical/fab_16x16.h>
#include <vertical/far_64x64.h>
#include <vertical/far_32x32.h>
#include <vertical/far_16x16.h>
#include <vertical/fas_64x64.h>
#include <vertical/fas_32x32.h>
#include <vertical/fas_16x16.h>

#ifdef UICONS_LEGACY_PROGMEM_FALLBACK
#undef PROGMEM
#undef UICONS_LEGACY_PROGMEM_FALLBACK
#endif