# uIcons developer convenience wrapper.
#
# This Makefile never replaces the canonical entry points: scripts/uicons for
# generation and scripts/quality.sh for the full quality gate. Every target
# below delegates to them, so each workflow step has exactly one
# implementation. Generation stays offline with the Python standard library
# only; no Inkscape, ImageMagick, or network access is required.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
BUILD_DIR ?= $(ROOT_DIR)/build
UICONS := $(PYTHON) $(ROOT_DIR)/scripts/uicons

EXAMPLES := $(wildcard $(ROOT_DIR)/examples/*.json)

.PHONY: help quality test build report package examples clean

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

quality: ## Run the full quality gate (or: scripts/quality.sh <phases> to iterate).
	@$(ROOT_DIR)/scripts/quality.sh

test: quality ## Alias for quality.

build: ## Build every example manifest into $(BUILD_DIR)/<name>/.
	@for manifest in $(EXAMPLES); do \
		name=$$(basename "$$manifest" .json); \
		echo "building $$name"; \
		$(UICONS) build --manifest "$$manifest" --output-dir "$(BUILD_DIR)/$$name"; \
	done

report: ## Print the footprint report for every example manifest.
	@for manifest in $(EXAMPLES); do \
		echo "=== $$(basename "$$manifest") ==="; \
		$(UICONS) report --manifest "$$manifest"; \
	done

examples: ## Build every PlatformIO example (native + AVR Uno + ESP32 smoke).
	@pio run -d $(ROOT_DIR)/examples/basic -e native -t exec
	@pio run -d $(ROOT_DIR)/examples/display_u8g2 -e uno
	@pio run -d $(ROOT_DIR)/examples/display_adafruit -e uno
	@pio run -d $(ROOT_DIR)/examples/display_tiny4koled -e uno
	@pio run -d $(ROOT_DIR)/examples/target_esp32 -e esp32dev

# Single implementation lives in scripts/quality.sh (phase_package, with leak
# and must-ship checks); this target only pins the output location.
package: ## Create the PlatformIO package tarball in $(BUILD_DIR)/.
	@UICONS_PACKAGE_OUTPUT="$(BUILD_DIR)/uicons.tar.gz" "$(ROOT_DIR)/scripts/quality.sh" package >/dev/null
	@echo "packaged $(BUILD_DIR)/uicons.tar.gz"

clean: ## Remove generated build output and Python caches.
	@rm -rf "$(BUILD_DIR)"
	@find "$(ROOT_DIR)" -name '__pycache__' -type d -prune -exec rm -rf {} +
	@find "$(ROOT_DIR)" -name '*.py[cod]' -delete
	@echo "cleaned"
