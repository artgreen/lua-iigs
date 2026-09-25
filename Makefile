# Lua 5.4.6 for the Apple IIgs: public build interface.
#
# This file only maps targets and options onto the shared Python tooling in
# tools/iigsbuild (one implementation of tool discovery, builds, tests,
# packaging, and provenance). Run 'make help' for commands and options.
# Machine-specific settings go in the untracked local.mk (see local.mk.example).

-include local.mk

PYTHON ?= python3
IIGS = $(PYTHON) tools/iigs.py

# Tool locations and compile concurrency, from local.mk or the command line.
export GOLDEN_GATE IIX ACX CP2 NULIB2 JOBS

# One orchestrator process per goal, run in order. The tooling also locks
# each build directory, so 'make -j' or two terminals cannot interleave
# ORCA runs. Compile concurrency is controlled by JOBS, not by make -j.
.NOTPARALLEL:
.DEFAULT_GOAL := all

opt = $(if $(strip $($(1))),$(2) "$(strip $($(1)))")

BUILD_TARGETS := all lua lua-small luac luatrace liblua liblua-small \
                 hosts iigshost allocfail bridge mmtest memfree everything
.PHONY: help doctor $(BUILD_TARGETS) test test-build suite identify package \
        hardware-suite stage kit release sizes clean verify-concurrency

help:
	@$(IIGS) help

doctor:
	@$(IIGS) doctor

$(BUILD_TARGETS):
	@$(IIGS) build $@

test:
	@$(IIGS) test $(call opt,BUILD,--build) $(call opt,CONFIG,--config) \
	  $(if $(strip $(CHECKS)),--checks $(CHECKS)) $(call opt,TIMEOUT,--timeout)

test-build:
	@$(IIGS) test-build

suite:
	@$(IIGS) suite $(call opt,BUILD,--build) $(call opt,CONFIG,--config) \
	  $(call opt,EXE,--exe) $(call opt,GROUP,--group) $(call opt,TIMEOUT,--timeout)

identify:
	@$(IIGS) identify $(call opt,BUILD_LABEL,--label) \
	  $(if $(strip $(CONFIGS)),--configs $(CONFIGS)) $(call opt,COMPARE_RELEASE,--compare-release)

package:
	@$(IIGS) package $(call opt,BUILD,--build) \
	  $(if $(strip $(KINDS)),--kinds $(KINDS)) $(call opt,REPORT,--report)

hardware-suite:
	@$(IIGS) hardware-suite $(call opt,BUILD,--build) $(call opt,RELEASE,--release) \
	  $(call opt,KIT,--kit) $(call opt,GROUP,--group) $(call opt,PREFIX,--prefix) \
	  $(call opt,PREFLIGHT,--preflight) $(if $(strip $(EXES)),--exe $(EXES))

stage:
	@$(IIGS) stage $(call opt,FROM,--from) $(call opt,DEST,--dest) $(if $(strip $(REPLACE)),--replace)

kit:
	@$(IIGS) kit $(call opt,BUILD_LABEL,--label)

sizes:
	@$(IIGS) sizes $(call opt,BUILD,--build)

verify-concurrency:
	@$(IIGS) verify-concurrency

clean:
	@$(IIGS) clean $(if $(strip $(DRY_RUN)),--dry-run)


# Assemble release candidates locally; this never uploads or rebuilds executables.
release:
	@$(IIGS) release $(call opt,BUILD,--build) $(call opt,REPORT,--report)
