"""Unit tests for the shared build tooling (no emulator required)."""
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from iigsbuild import batch, clean, configs, contracts, identified, orca, packaging, stage  # noqa: E402
from iigsbuild.builder import include_closure  # noqa: E402
from iigsbuild.common import BuildError  # noqa: E402


class Configurations(unittest.TestCase):
    def test_parser_modes(self):
        full, small, luac = (configs.get(n).parseconf() for n in ("lua", "lua-small", "luac"))
        self.assertIn("#define BUILD_IS_LUA\n", full)
        self.assertNotIn("LUA_NO_PARSER", full)
        self.assertIn("#define BUILD_IS_LUA\n", small)
        self.assertIn("#define LUA_NO_PARSER\n", small)
        self.assertIn("#define BUILD_IS_LUAC\n", luac)
        self.assertNotIn("LUA_NO_PARSER", luac)  # compiler always has the parser
        self.assertNotIn("BUILD_IS_LUA\n", luac)
        self.assertIn("LUA_IIGS_MMTRACE", configs.get("luatrace").parseconf())

    def test_generated_header_is_guarded_and_carries_build_id(self):
        text = configs.get("lua").parseconf("IIgs abc123 plain")
        self.assertTrue(text.index("#ifndef parseconf_h") < text.index("#define BUILD_IS_LUA"))
        self.assertIn('#define LUA_IIGS_BUILD_ID "IIgs abc123 plain"', text)
        for bad in ('x"y', "a\\b", "", "x" * 65, "semi;colon"):
            with self.subTest(bad=bad), self.assertRaises(BuildError):
                configs.get("lua").parseconf(bad)

    def test_link_order_matches_historical_recipe(self):
        full = configs.get("lua").link_inputs()
        self.assertEqual(full[:2], ["lua.a", "lvm"])
        self.assertEqual([x[:-2] for x in full[2:]], list(configs.CORE_UNITS))
        self.assertEqual(configs.get("luac").link_inputs()[0], "luac.a")

    def test_compact_omits_parser_units_only(self):
        small = configs.get("lua-small")
        self.assertEqual(set(configs.CORE_UNITS) - set(small.core_units()), set(configs.PARSER_UNITS))
        self.assertFalse(any(u + ".a" in small.link_inputs() for u in configs.PARSER_UNITS))
        self.assertFalse(any(u + ".a" in small.lib_members() for u in configs.PARSER_UNITS))

    def test_tracked_sources_do_not_carry_configuration(self):
        self.assertNotIn("src/parseconf.h", clean.tracked())
        self.assertIn("/src/parseconf.h", (ROOT / ".gitignore").read_text())
        luaconf = (ROOT / "src/luaconf.h").read_text()
        self.assertIn('#include "parseconf.h"', luaconf)
        self.assertNotIn("\n#define LUA_NO_PARSER", luaconf)
        self.assertIn('#include "parseconf.h"', (ROOT / "src/llex.c").read_text())


class Dependencies(unittest.TestCase):
    def test_include_closure_follows_search_order(self):
        with tempfile.TemporaryDirectory() as temp:
            gen, src = Path(temp, "gen"), Path(temp, "src")
            gen.mkdir(), src.mkdir()
            (src / "a.c").write_text('#include "b.h"\n#include "parseconf.h"\n#include <stdio.h>\n')
            (src / "b.h").write_text('  #  include "c.h"\n')
            (src / "c.h").write_text("")
            (src / "parseconf.h").write_text("stale")
            (gen / "parseconf.h").write_text("generated")
            found = include_closure(src / "a.c", [gen, src])
            self.assertEqual({p.name for p in found}, {"b.h", "c.h", "parseconf.h"})
            self.assertIn((gen / "parseconf.h").resolve(), found)  # generated one wins
            self.assertNotIn((src / "parseconf.h").resolve(), found)

    def test_real_sources_resolve_generated_config(self):
        with tempfile.TemporaryDirectory() as temp:
            gen = Path(temp)
            (gen / "parseconf.h").write_text("")
            for unit in ("llex", "ldo", "lapi", "lcode"):
                names = {p.name for p in include_closure(ROOT / "src" / (unit + ".c"), [gen, ROOT / "src"])}
                self.assertIn("parseconf.h", names, unit)  # every unit sees it via luaconf.h


class Batches(unittest.TestCase):
    def test_rules(self):
        steps = [batch.Step("a", "luatest", ["-E", "x.lua"]),
                 batch.Step("b", "luactest", ["-p", "bad.lua"], capture=("bad.log", "st"), echo="step b")]
        text = batch.render("Title", steps, "20:")
        self.assertEqual(text, "* Title\nset exit on\n20:luatest -E x.lua\necho step b\nunset exit\n"
                               "20:luactest -p bad.lua >&bad.log\nset st {status}\nset exit on\nexit 0\n")
        self.assertIn("\nluatest -E x.lua\n", batch.render("Title", steps, ""))
        for prefix in ("20", "20:;x", "a:", "20:\necho"):
            with self.subTest(prefix=prefix), self.assertRaises(BuildError):
                batch.render("T", steps, prefix)
        with self.assertRaises(BuildError):
            batch.render("No; semicolons in comments", steps)

    def test_kit_batches_have_no_semicolons(self):
        from iigsbuild import kits
        for text in (kits.luac_batch(), kits.host_batch()):
            self.assertNotIn(";", text)
            self.assertTrue(text.endswith("exit 0\n"))


class Packaging(unittest.TestCase):
    def test_types_use_names_not_numbers(self):
        # acx silently stores NON $00 for numeric types; names are required.
        for kind, (name, ftype, aux) in packaging.TYPES.items():
            self.assertRegex(name, r"^[A-Z]{3}$")
        self.assertEqual(packaging.TYPES["EXE"][1:], (0xB5, 0))
        self.assertEqual(packaging.TYPES["EXEC"][1:], (0xB0, 6))
        self.assertEqual(packaging.TYPES["CSRC"][1:], (0xB0, 8))
        self.assertEqual(packaging.TYPES["LIB"][1:], (0xB2, 0))
        self.assertEqual(packaging.TYPES["OBJ"][1:], (0xB1, 0))

    def test_text_gets_cr_and_binaries_stay_exact(self):
        self.assertEqual(packaging.Member("A.TXT", b"a\r\nb\nc", "TXT").native, b"a\rb\rc")
        self.assertEqual(packaging.Member("TEST", b"x\n", "EXEC").native, b"x\r")
        raw = bytes(range(256))
        self.assertEqual(packaging.Member("LUA", raw, "EXE").native, raw)
        self.assertEqual(packaging.Member("X.LUO", raw, "BIN").native, raw)

    def test_names_are_prodos(self):
        for bad in ("1LUA", "LUA-SMALL", "A" * 16, "", "LUA SMALL"):
            with self.subTest(bad=bad), self.assertRaises(BuildError):
                packaging.Member(bad, b"", "TXT")

    def test_catalog_parser(self):
        text = ("Type Auxtyp Modified Format Length Size Name\n---- ------\n"
                "EXE  $0000  24-Sep-26 17:23 LZW/2   362361  52% LUA\n"
                "SRC  $0006  24-Sep-26 17:23        2      512  *TEST\n")
        rows = {m.group(3): (m.group(1), m.group(2)) for m in packaging.CATALOG.finditer(text)}
        self.assertEqual(rows, {"LUA": ("EXE", "0000"), "TEST": ("SRC", "0006")})


class Identity(unittest.TestCase):
    def fake_toolchain(self):
        return types.SimpleNamespace(identity=lambda: {"orca_c": "2.2.1", "iix": "x", "sdk_files_sha256": {}})

    def test_build_id_covers_runtime_sources_only(self):
        tc = self.fake_toolchain()
        base = {"src/lapi.c": b"one"}
        self.assertEqual(identified.build_digest(tc, base), identified.build_digest(tc, dict(base)))
        self.assertNotEqual(identified.build_digest(tc, base),
                            identified.build_digest(tc, {"src/lapi.c": b"two"}))
        inputs = identified.runtime_inputs()
        self.assertTrue(all(k.startswith("src/") for k in inputs))
        self.assertIn("src/lua.hpp", inputs)
        self.assertNotIn("HARDWARE_TESTING.md", inputs)  # docs do not change the build ID

    def test_toolchain_change_changes_build_id(self):
        a = self.fake_toolchain()
        b = types.SimpleNamespace(identity=lambda: {"orca_c": "2.2.2", "iix": "x", "sdk_files_sha256": {}})
        self.assertNotEqual(identified.build_digest(a, {}), identified.build_digest(b, {}))


class Cleaning(unittest.TestCase):
    def test_allow_list_never_covers_evidence(self):
        self.assertFalse(any(p.startswith(("build/", "docs", "dist")) for p in clean.LEGACY_IN_TREE))
        for keep in ("builds", "packages", "hardware-suites", "test-reports", "hardware",
                     "diagnostics", "archive", "worktrees", "release-*"):
            self.assertIn(keep, clean.PRESERVED)

    def test_tracked_files_are_never_candidates(self):
        tracked = clean.tracked()
        self.assertTrue(tracked)
        self.assertFalse({str(p.relative_to(ROOT)) for p in clean.legacy_in_tree()} & tracked)


class Staging(unittest.TestCase):
    def test_refuses_to_replace_without_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            src, dest = Path(temp, "pkg"), Path(temp, "nas", "lua.test")
            src.mkdir(), dest.mkdir(parents=True)
            (src / "TEST.SHK").write_bytes(b"new")
            packaging.write_sums(src, ["TEST.SHK"])
            (dest / "TEST.SHK").write_bytes(b"old")
            args = types.SimpleNamespace(source=src, dest=dest, replace=False)
            with self.assertRaises(BuildError):
                stage.stage(args)
            self.assertEqual((dest / "TEST.SHK").read_bytes(), b"old")
            args.replace = True
            stage.stage(args)
            self.assertEqual((dest / "TEST.SHK").read_bytes(), b"new")
            backups = list(dest.glob("replaced-*/TEST.SHK"))
            self.assertEqual([b.read_bytes() for b in backups], [b"old"])

    def test_refuses_corrupted_source(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp, "pkg")
            src.mkdir()
            (src / "TEST.SHK").write_bytes(b"good")
            packaging.write_sums(src, ["TEST.SHK"])
            (src / "TEST.SHK").write_bytes(b"tampered")
            with self.assertRaises(BuildError):
                stage.stage(types.SimpleNamespace(source=src, dest=Path(temp, "out"), replace=False))


class ToolOutput(unittest.TestCase):
    def test_orca_error_detection(self):
        self.assertRegex("1 error found.\n", orca.COMPILE_ERRORS)
        self.assertRegex("Terminal error: Error reading hdr.h", orca.COMPILE_ERRORS)
        self.assertNotRegex("", orca.COMPILE_ERRORS)
        self.assertRegex("Error at 00000001 past f PC = 0000001E : Unresolved reference Label: g",
                         orca.LINK_ERRORS)
        self.assertRegex("1 error found during link", orca.LINK_ERRORS)
        self.assertNotRegex("There is 1 segment, for a length of $00000930 bytes.", orca.LINK_ERRORS)

    def test_link_map_symbols(self):
        text = ("0000004C P 04 00 CLIBS                      0000825B G 02 00 ERROROUTPUT\n"
                "0000250D G 09 00 luaY_nvarstack             000069A7 G 09 00 luaY_parser\n")
        self.assertEqual(orca.link_symbols(text), {"CLIBS", "ERROROUTPUT", "luaY_nvarstack", "luaY_parser"})


class CompactPlan(unittest.TestCase):
    def test_plan_is_consistent(self):
        plan = contracts.compact_manifest()
        self.assertIn("nosource", plan["groups"]["debug"])
        self.assertIn("nosource", plan["groups"]["stripped"])
        self.assertTrue(set(plan["requires_parser"]).isdisjoint(plan["groups"]["debug"]))

    def test_nosource_contract_checks_parser_mode(self):
        out = "NOSOURCE 1 PASSED parser=yes checks=129\n"
        contracts.validate("nosource", out, parser=True)
        with self.assertRaises(ValueError):
            contracts.validate("nosource", out, parser=False)


if __name__ == "__main__":
    unittest.main()
