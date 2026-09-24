"""Check batch error handling and probe rejection of false success."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("luac_kit", ROOT / "tools/luac-test-kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class LuacKitChecks(unittest.TestCase):
    def test_batch_captures_expected_failure_status_before_another_command(self):
        script = kit.batch()
        for name in ("bad", "deep"):
            self.assertIn(f"unset exit\n20:luactest -p lc.{name}.lua >&lc.{name}.log\n"
                          "set lcstatus {status}\nset exit on\n", script)
        self.assertTrue(script.endswith("20:luatest -E test.lua finish\nexit 0\n"))
        self.assertEqual(script.count("unset exit\n"), 2)

    def test_comment_does_not_contain_command_separator(self):
        self.assertNotIn(";", kit.batch())

    def test_executable_prefix_is_configurable(self):
        script = kit.batch("15:")
        self.assertNotIn("20:", script)
        self.assertIn("15:luatest -E -v test.lua prepare", script)
        self.assertIn("15:luactest -v", script)
        self.assertIn("\nluactest -v\n", kit.batch(""))

    def test_prefix_cannot_inject_shell_commands(self):
        for prefix in ("20:;exit", "20:\necho", "20", "arbitrary:"):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                kit.batch(prefix)

    @unittest.skipUnless(os.environ.get("TEST_LUA"), "set TEST_LUA for IIgs probe fault injection")
    def test_missing_stages_and_unrelated_errors_cannot_pass(self):
        parent = ROOT / "build/diagnostics"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            stage = Path(temp)
            (stage / "test.lua").write_bytes((ROOT / "tests/luacprobe.lua").read_bytes())
            command = [os.environ.get("IIX", "iix"), "--memcheck", str(Path(os.environ["TEST_LUA"]).resolve()),
                       "-E", "test.lua"]
            def run(*args):
                return subprocess.run(command + list(args), cwd=stage, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            prepared = run("prepare")
            self.assertEqual(prepared.returncode, 0, prepared.stdout)
            cases = [("finish", [], "compiler test did not finish every phase"),
                     ("syntax", ["0"], "compiler unexpectedly accepted invalid source"),
                     ("syntax", ["255"], "wrong compiler error")]
            (stage / "lc.bad.log").write_text("luactest: cannot open lc.bad.lua: no such file\n")
            for phase, args, reason in cases:
                with self.subTest(phase=phase, args=args):
                    result = run(phase, *args)
                    text = result.stdout.decode(errors="replace")
                    self.assertNotEqual(result.returncode, 0, text)
                    self.assertIn(reason, text)
                    self.assertNotIn("LUACPROBE 1 PASSED", text)
                    self.assertNotIn("MemCheck:", text)


if __name__ == "__main__":
    unittest.main()
