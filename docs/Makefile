# Licensed to Crate (https://crate.io) under one or more contributor license
# agreements.  See the NOTICE file distributed with this work for additional
# information regarding copyright ownership.  Crate licenses this file to you
# under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License.  You may obtain a copy of the
# License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.
#
# However, if you have executed another commercial license agreement with Crate
# these terms will supersede the license and you may use the software solely
# pursuant to the terms of the relevant commercial agreement.


# =============================================================================
# Crate Docs
# =============================================================================

# The Crate Docs project provides a common set of tools for producing the
# Crate.io documentation. See <https://github.com/crate/crate-docs/> for more
# information.

# This file is taken from the demo Sphinx project available at
# <https://github.com/crate/crate-docs/blob/main/docs>. This demo docs project
# provides a reference implementation that should be copied for all Sphinx
# projects at Crate.io.

# The Crate Docs build system works by centralizing its core components in the
# `crate-docs` repository. At build time, this Makefile creates a copy of the
# this project under the `.crate-docs` directory. This Makefile is an interface
# for those core components.


# Upgraded instructions
# -----------------------------------------------------------------------------

# You must pin your Sphinx project to a specific version of the Crate Docs
# project. You can do this by editing the `build.json` file. Change the JSON
# `message` value to the desired release number. A list of releases is
# available at <https://github.com/crate/crate-docs/releases>.

# Although care has been taken to restrict changes to the core components, you
# may occasionally need to update your project to match the reference
# implementation. Check the release notes for any special instructions.


# Project-specific customization
# =============================================================================

# If you want to customize the build system for your Sphinx project, add lines
# to this section.


# Build system integration
# =============================================================================

# This is a boilerplate section is required for integration with the Crate Docs
# build system. All Sphinx projects using a the same Crate Docs version
# should have exactly the same boilerplate.

# IF YOU ARE EDITING THIS FILE IN A REAL SPHINX PROJECT, YOU SHOULD NOT MAKE
# ANY CHANGES TO THIS SECTION.

# If you want to make changes to the boilerplate, please make a pull request on
# the demo Sphinx project in the Crate Docs repository available at
# <https://github.com/crate/crate-docs/blob/main/docs>.

.EXPORT_ALL_VARIABLES:

DOCS_DIR      := docs
TOP_DIR       := ..
BUILD_JSON    := build.json
BUILD_REPO    := https://github.com/crate/crate-docs.git
LATEST_BUILD  := https://github.com/crate/crate-docs/releases/latest
CLONE_DIR     := .crate-docs
SRC_DIR       := $(CLONE_DIR)/common-build
SELF_SRC      := $(TOP_DIR)/common-build
SELF_MAKEFILE := $(SELF_SRC)/rules.mk
SRC_MAKE      := $(MAKE) -f $(SRC_DIR)/rules.mk

# Parse the JSON file
BUILD_VERSION := $(shell cat $(BUILD_JSON) | \
    python -c 'import json, sys; print(json.load(sys.stdin)["message"])')

ifeq ($(BUILD_VERSION),)
$(error No build version specified in `$(BUILD_JSON)`.)
endif

# This is a non-essential check so we timeout after only two seconds so as not
# to frustrate the user when there are network issues
LATEST_VERSION := $(shell curl -sI --connect-timeout 2 '$(LATEST_BUILD)' | \
    grep -i 'Location:' | grep -Eoh '[^/]+$$')

# Skip if no version could be determined (i.e., because of a network error)
ifneq ($(LATEST_VERSION),)
# Only issue a warning if there is a version mismatch
ifneq ($(BUILD_VERSION),$(LATEST_VERSION))
define version_warning
You are using Crate Docs version $(BUILD_VERSION), however version \
$(LATEST_VERSION) is available. You should consider upgrading. Follow the \
instructions in `Makefile` and then run `make reset`.
endef
endif
endif

# Default rule
.PHONY: help
help: $(CLONE_DIR)
	@ $(MAKE) version-warn
	@ $(SRC_MAKE) $@

.PHONY: version-warn
version-warn:
	@ # Because version numbers may vary in length, we must wrap the warning
	@ # message at run time to be sure of correct output
	@ if test -n '$(version_warning)'; then \
	      printf '\033[33m'; \
	      echo '$(version_warning)' | fold -w 79 -s; \
	      printf '\033[00m\n'; \
	  fi

ifneq ($(wildcard $(SELF_MAKEFILE)),)
# The project detects itself and fakes an install of its own core build rules
# so that it can test itself
$(CLONE_DIR):
	@ printf '\033[1mInstalling the build system...\033[00m\n'
	@ mkdir -p $@
	@ cp -R $(SELF_SRC) $(SRC_DIR)
	@ printf 'Created: $(CLONE_DIR)\n'
else
# All other projects install a versioned copy of the core build rules
$(CLONE_DIR):
	@ printf '\033[1mInstalling the build system...\033[00m\n'
	@ git clone --depth=1 -c advice.detachedHead=false \
	    --branch=$(BUILD_VERSION) $(BUILD_REPO) $(CLONE_DIR)
	@ printf 'Created: $(CLONE_DIR)\n'
endif

# Don't pass through this target
.PHONY: Makefile
Makefile:

# By default, pass targets through to the core build rules
.PHONY:
%: $(CLONE_DIR)
	@ $(MAKE) version-warn
	@ $(SRC_MAKE) $@

.PHONY: reset
reset:
	@ printf '\033[1mResetting the build system...\033[00m\n'
	@ rm -rf $(CLONE_DIR)
	@ printf 'Removed: $(CLONE_DIR)\n'
