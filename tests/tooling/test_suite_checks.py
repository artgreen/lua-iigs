"""Regression contracts for the repeatable suite, including misleading logs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from iigsbuild import contracts, suite  # noqa: E402


class SuiteChecks(unittest.TestCase):
    def setUp(self):
        self.data = contracts.suite_manifest()
        self.good = ("SUITE PASS hwsmoke\nSUITE PASS numconv WITH SKIPS\n"
                     "SUITE COMPLETE group=smoke passed=2 failed=0 with_skips=1\n")

    def check(self, text):
        return contracts.validate_suite(text, "smoke", self.data["groups"])

    def test_success_retains_partial_coverage(self):
        self.assertEqual(self.check(self.good)["status"], "passed with skips")

    def test_truncated_run_cannot_pass(self):
        with self.assertRaises(ValueError):
            self.check(self.good.split("SUITE COMPLETE")[0])

    def test_summary_alone_cannot_pass(self):
        with self.assertRaises(ValueError):
            self.check(self.good.splitlines()[-1])

    def test_missing_duplicate_or_reordered_cases_fail(self):
        for text in (self.good.replace("SUITE PASS hwsmoke\n", ""),
                     "SUITE PASS hwsmoke\n" + self.good,
                     self.good.replace("hwsmoke", "TEMP").replace("numconv", "hwsmoke").replace("TEMP", "numconv")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check(text)

    def test_inconsistent_summary_fails(self):
        for text in (self.good.replace("passed=2", "passed=1"),
                     self.good.replace("with_skips=1", "with_skips=0"),
                     self.good + self.good.splitlines()[-1] + "\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check(text)

    def test_error_overrides_summary(self):
        for problem in ("MemCheck: memory altered", "BRK", "SUITE FAIL io", "mm=degraded"):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                self.check(self.good + problem)

    def test_full_contains_all_targeted_and_io_regressions(self):
        from iigsbuild.contracts import TESTS
        self.assertTrue(set(TESTS) <= set(self.data["groups"]["full"]))
        self.assertTrue({"files", "ioprobe", "bufprobe", "largefile", "bigio", "bytefile", "filelife"}
                        <= set(self.data["groups"]["full"]))

    @unittest.skipUnless(os.environ.get("TEST_LUA"), "set TEST_LUA for IIgs runner fault injection")
    def test_driver_rejects_incomplete_and_false_success(self):
        # Exercise the real Lua observer/abort path, not just the Python parser.
        cases = {
            "printed-failure": 'print("SMOKE DONE - expect shell prompt next"); print("FAIL injected")',
            "no-marker": 'print("incidental OK")',
            "error-after-marker": 'print("SMOKE DONE - expect shell prompt next"); error("injected")',
        }
        reasons = {"printed-failure": "SUITE FAIL hwsmoke: FAIL injected",
                   "no-marker": "SUITE FAIL hwsmoke: missing completion marker",
                   "error-after-marker": "hwsmoke.lua:1: injected"}
        scratch = ROOT / "build/test-runs"
        scratch.mkdir(parents=True, exist_ok=True)
        for name, source in cases.items():
            # GoldenGate cannot resolve the macOS system-temp alias reliably.
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=scratch) as temp:
                stage = suite.prepare(Path(temp), Path(os.environ["TEST_LUA"]), self.data)
                (stage / "hwsmoke.lua").write_text(source)
                result = subprocess.run([os.environ.get("IIX", "iix"), "--memcheck",
                                         str(stage / "luatest"), "-E", "test.lua", "smoke"],
                                        cwd=stage, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
                text = result.stdout.decode(errors="replace")
                self.assertNotEqual(result.returncode, 0, text)
                self.assertIn(reasons[name], text)
                self.assertNotIn("MemCheck:", text)
                self.assertNotIn("SUITE START 2/", text)
                self.assertNotRegex(text, r"(?m)^SUITE COMPLETE")


if __name__ == "__main__":
    unittest.main()
