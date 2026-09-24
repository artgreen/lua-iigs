"""Build configurations and the per-build generated parseconf.h.

Each configuration has its own directory, objects, libraries, and
parseconf.h. src/luaconf.h includes parseconf.h, so every translation unit
(and every embedding host) sees the same parser/compiler selection. No
tracked file is rewritten when switching configurations.

Compile flags, unit lists, and link order reproduce the historical
src/Makefile exactly for the full interpreter, compiler, and library.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional, Tuple

from .common import BuildError

COMPILE_FLAGS = ("-I", "-P", "-D", "+O")
# Historical src/Makefile order; link order affects code layout.
CORE_UNITS = ("lapi", "lauxlib", "lbaselib", "lcode", "lcorolib", "lctype", "ldblib",
              "ldebug", "ldo", "ldump", "lfunc", "lgc", "linit", "liolib", "llex",
              "lmathlib", "lmem", "loadlib", "lobject", "lopcodes", "loslib", "lparser",
              "lstate", "lstring", "lstrlib", "ltable", "ltablib", "ltm", "lundump", "lzio")
# Source-parser and code-generator units. A parser-free build neither
# compiles nor links them; the linker proves nothing still refers to them.
PARSER_UNITS = ("lcode", "llex", "lparser")
PARSER_SYMBOLS = ("luaY_parser", "luaK_code", "luaX_next", "luaX_init")
BUILD_ID = re.compile(r"[A-Za-z0-9 .:_+-]{1,64}")


@dataclass(frozen=True)
class Config:
    name: str              # make target / directory name
    main: str              # 'lua' or 'luac' (the main translation unit)
    parser: bool
    exe: str               # ProDOS-valid executable name
    variant: Optional[str]  # banner word for identified builds (None: no banner)
    lib: Optional[str] = None
    trace: bool = False
    summary: str = ""

    @property
    def role(self) -> str:
        return "BUILD_IS_LUAC" if self.main == "luac" else "BUILD_IS_LUA"

    def macros(self, build_id: Optional[str] = None) -> List[Tuple[str, Optional[str]]]:
        macros: List[Tuple[str, Optional[str]]] = [(self.role, None)]
        if not self.parser:
            macros.append(("LUA_NO_PARSER", None))
        if self.trace:
            macros.append(("LUA_IIGS_MMTRACE", None))
        if build_id is not None:
            if not BUILD_ID.fullmatch(build_id):
                raise BuildError(f"build ID must be 1-64 plain ASCII characters: {build_id!r}")
            macros.append(("LUA_IIGS_BUILD_ID", '"' + build_id + '"'))
        return macros

    def parseconf(self, build_id: Optional[str] = None) -> str:
        lines = [f"/* Generated for build configuration '{self.name}'. Do not edit;",
                 "** each configuration directory has its own copy. */",
                 "#ifndef parseconf_h", "#define parseconf_h"]
        for name, value in self.macros(build_id):
            lines.append(f"#define {name}" + (f" {value}" if value is not None else ""))
        lines.append("#endif")
        return "\n".join(lines) + "\n"

    def core_units(self) -> List[str]:
        return [u for u in CORE_UNITS if self.parser or u not in PARSER_UNITS]

    def link_inputs(self) -> List[str]:
        """Arguments for 'iix link', matching the historical recipe."""
        return [self.main + ".a", "lvm", *[u + ".a" for u in self.core_units()]]

    def lib_members(self) -> List[str]:
        return [u + ".a" for u in self.core_units()]


CONFIGS = {c.name: c for c in (
    Config("lua", "lua", True, "lua", "plain", lib="lua.lib",
           summary="full interpreter with the source parser; full embedding library"),
    Config("lua-small", "lua", False, "luasmall", "small", lib="luasmall.lib",
           summary="compact bytecode-only interpreter (LUA_NO_PARSER); parser-free library"),
    Config("luac", "luac", True, "luac", None,
           summary="bytecode compiler; always parser-enabled"),
    Config("luatrace", "lua", True, "luatrace", "trace", trace=True,
           summary="full interpreter with Memory Manager tracing (LUA_IIGS_MMTRACE)"),
)}

# Hosts and probes linked against the full configuration's library.
HOSTS = {
    "iigshost": {"sources": ["tests/iigshost.c"], "lua": True,
                 "summary": "native embedding / C-hook regression host"},
    "allocfail": {"sources": ["tests/allocfail.c"], "lua": True,
                  "summary": "allocator fault injection (includes lauxlib.c)"},
    "bridge": {"sources": ["test.c", "testiface.c", "testbridge.c"], "lua": True,
               "summary": "C bridge embedding demo"},
    "mmtest": {"sources": ["mmtest.c"], "lua": False, "summary": "raw Memory Manager probe"},
    "memfree": {"sources": ["memfree.c"], "lua": False,
                "summary": "memory report; needs real hardware tools to run"},
}


def get(name: str) -> Config:
    try:
        return CONFIGS[name]
    except KeyError:
        raise BuildError(f"unknown configuration {name!r}; choose one of: {', '.join(CONFIGS)}") from None
