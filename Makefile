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

.PHONY: help quality test build report package clean

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

quality: ## Run the full quality gate (format, tests, drift, analysis, package).
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

package: ## Create the PlatformIO package tarball in $(BUILD_DIR)/.
	@mkdir -p "$(BUILD_DIR)"
	@pio pkg pack --output "$(BUILD_DIR)/uicons.tar.gz" "$(ROOT_DIR)" >/dev/null
	@echo "packaged $(BUILD_DIR)/uicons.tar.gz"

clean: ## Remove generated build output and Python caches.
	@rm -rf "$(BUILD_DIR)"
	@find "$(ROOT_DIR)" -name '__pycache__' -type d -prune -exec rm -rf {} +
	@find "$(ROOT_DIR)" -name '*.py[cod]' -delete
	@echo "cleaned"
