"""Shared build, test, and packaging tooling for Lua on the Apple IIgs.

The Makefile at the repository root is the public interface. Every command
it offers is implemented here, so tool discovery, build orchestration,
packaging, checksums, metadata verification, and test reporting have one
implementation. Standard library only; Python 3.9 or later.
"""

RECIPE_VERSION = 1  # bump when compile/link/package recipes change meaning
