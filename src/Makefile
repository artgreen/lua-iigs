# Deprecated: builds run from the repository root ('make help').
# The historical recipe (flags, unit list, link order) now lives in
# tools/iigsbuild/configs.py. These forwards never write into src/: objects
# and the generated parseconf.h go under build/dev/<configuration>/.
.NOTPARALLEL:
.PHONY: lua luac liblua all clean run

lua luac liblua all clean:
	@echo "src/Makefile is deprecated; running 'make $@' at the repository root." >&2
	@$(MAKE) --no-print-directory -C .. $@

run:
	@echo "src/Makefile 'run' was removed; use: make lua, then iix build/dev/lua/out/lua test.lua" >&2
	@exit 2

.DEFAULT:
	@echo "src/Makefile target '$@' is obsolete (luac.lib, lua_conf, luac_conf, rmlib ...)." >&2
	@echo "Run 'make help' at the repository root." >&2
	@exit 2
